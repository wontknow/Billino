"""
Backend configuration management with validation.

This module provides:
- Configuration loading from environment variables
- Configuration validation (ports, hosts, paths)
- Startup health checks
"""

import socket
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator

from utils import logger


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class BackendConfig(BaseModel):
    """
    Billino backend configuration with validation.

    All values are loaded from environment variables and validated
    on instantiation to catch configuration errors early.
    """

    # Network Configuration
    host: str = "127.0.0.1"
    port: int = 8000
    environment: Environment = Environment.DEVELOPMENT

    # Database Configuration
    db_url: Optional[str] = None
    db_path: Optional[Path] = None

    # Feature Flags
    backup_enabled: bool = True
    tauri_enabled: bool = False

    # Backup Configuration
    backup_schedule_hour: int = 2
    backup_schedule_minute: int = 0
    backup_retention_days: int = 30

    # CORS Configuration
    allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number is in valid range."""
        if not 1024 <= v <= 65535:
            raise ValueError(f"Port must be between 1024 and 65535, got {v}")
        return v

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host address."""
        if not v or v.strip() == "":
            raise ValueError("Host cannot be empty")
        # Don't validate that host is resolvable - might fail in some environments
        return v

    @field_validator("backup_schedule_hour")
    @classmethod
    def validate_backup_hour(cls, v: int) -> int:
        """Validate backup hour (0-23)."""
        if not 0 <= v <= 23:
            raise ValueError(f"Backup hour must be 0-23, got {v}")
        return v

    @field_validator("backup_schedule_minute")
    @classmethod
    def validate_backup_minute(cls, v: int) -> int:
        """Validate backup minute (0-59)."""
        if not 0 <= v <= 59:
            raise ValueError(f"Backup minute must be 0-59, got {v}")
        return v

    @field_validator("backup_retention_days")
    @classmethod
    def validate_retention_days(cls, v: int) -> int:
        """Validate backup retention days."""
        if v <= 0:
            raise ValueError(f"Backup retention days must be > 0, got {v}")
        return v

    @classmethod
    def from_env(cls) -> "BackendConfig":
        """
        Load configuration from environment variables.

        Environment variables:
        - BACKEND_HOST: Server host (default: 127.0.0.1)
        - BACKEND_PORT: Server port (default: 8000)
        - ENV: Environment (development|production|testing, default: development)
        - BILLINO_DB_URL: Database URL override (optional)
        - BACKUP_ENABLED: Enable backup system (default: true)
        - TAURI_ENABLED: Is running in Tauri context (default: false)
        - BACKUP_SCHEDULE_HOUR: Hour for daily backup (0-23, default: 2)
        - BACKUP_SCHEDULE_MINUTE: Minute for daily backup (0-59, default: 0)
        - BACKUP_RETENTION_DAYS: Days to keep backups (default: 30)
        - ALLOWED_ORIGINS: CORS origins CSV (default: http://localhost:3000)

        Returns:
            BackendConfig: Validated configuration

        Raises:
            ValueError: If configuration validation fails
        """
        import os

        # Parse environment variables
        host = os.getenv("BACKEND_HOST", "127.0.0.1")
        port = int(os.getenv("BACKEND_PORT", "8000"))
        env = os.getenv("ENV", "development")
        db_url = os.getenv("BILLINO_DB_URL")
        backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
        tauri_enabled = os.getenv("TAURI_ENABLED", "false").lower() == "true"
        backup_hour = int(os.getenv("BACKUP_SCHEDULE_HOUR", "2"))
        backup_minute = int(os.getenv("BACKUP_SCHEDULE_MINUTE", "0"))
        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
        allowed_origins = [o.strip() for o in origins.split(",")]

        return cls(
            host=host,
            port=port,
            environment=Environment(env),
            db_url=db_url,
            backup_enabled=backup_enabled,
            tauri_enabled=tauri_enabled,
            backup_schedule_hour=backup_hour,
            backup_schedule_minute=backup_minute,
            backup_retention_days=retention_days,
            allowed_origins=allowed_origins,
        )

    def server_url(self) -> str:
        """Return the full server URL."""
        return f"http://{self.host}:{self.port}"

    def is_port_available(self) -> bool:
        """
        Check if the configured port is available.

        Returns:
            bool: True if port is available, False if already bound

        Raises:
            Exception: If port check fails for other reasons
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Allow reuse of port in TIME_WAIT state (cross-platform)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.close()
            return True
        except socket.error as e:
            if e.errno == 48 or e.errno == 98:  # macOS, Linux: Address already in use
                return False
            if e.errno == 10048:  # Windows: Address already in use
                return False
            raise


def validate_startup_conditions(config: BackendConfig) -> dict:
    """
    Validate all startup conditions.

    Checks:
    - Port availability
    - Database path accessibility (if using local file)
    - Log directory accessibility

    Args:
        config: Backend configuration

    Returns:
        dict: Validation result with 'valid' bool and 'errors' list

    Example:
        ```python
        config = BackendConfig.from_env()
        result = validate_startup_conditions(config)
        if not result['valid']:
            logger.error(f"Startup validation failed: {result['errors']}")
            sys.exit(1)
        ```
    """
    errors = []
    warnings = []

    # Check port availability
    if not config.is_port_available():
        errors.append(
            f"❌ Port {config.port} is already in use. "
            f"Check for running instances or change BACKEND_PORT."
        )

    # Check database path (if using SQLite)
    if config.db_url and "sqlite" in config.db_url:
        # Extract path from SQLite URL (sqlite:///path/to/db.db)
        db_path = config.db_url.replace("sqlite:///", "")
        if db_path:
            db_dir = Path(db_path).parent
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 Created database directory: {db_dir}")
                except Exception as e:
                    errors.append(f"❌ Cannot create database directory {db_dir}: {e}")
            elif not db_dir.is_dir():
                errors.append(
                    f"❌ Database path exists but is not a directory: {db_dir}"
                )

    # Check log directory
    log_dir = Path(__file__).parent.parent / "logs"
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 Created log directory: {log_dir}")
        except Exception as e:
            warnings.append(f"⚠️ Cannot create log directory {log_dir}: {e}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
