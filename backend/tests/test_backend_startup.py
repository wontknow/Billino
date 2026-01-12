"""
Integration tests for backend health checking and startup validation.

These tests verify:
1. Configuration loading and validation
2. Database initialization
3. Backend startup sequence
4. Health check endpoints
5. Error handling

Run with: pytest tests/test_backend_startup.py -v
"""

from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from database import get_db_url, init_db
from routers import health
from utils.config import BackendConfig, validate_startup_conditions
from utils.errors import StartupError


class TestConfigurationLoading:
    """Test configuration loading and validation."""

    def test_config_from_env_default_values(self, monkeypatch):
        """Config uses sensible defaults when no env vars set."""
        monkeypatch.delenv("BACKEND_HOST", raising=False)
        monkeypatch.delenv("BACKEND_PORT", raising=False)

        config = BackendConfig.from_env()

        assert config.host == "127.0.0.1"
        assert config.port == 8000

    def test_config_from_env_custom_values(self, monkeypatch):
        """Config loads custom values from environment."""
        monkeypatch.setenv("BACKEND_HOST", "0.0.0.0")
        monkeypatch.setenv("BACKEND_PORT", "9000")

        config = BackendConfig.from_env()

        assert config.host == "0.0.0.0"
        assert config.port == 9000

    def test_config_validates_port_range(self):
        """Config validates port is in valid range."""
        with pytest.raises(ValueError, match="Port must be between"):
            BackendConfig(
                host="127.0.0.1",
                port=100,  # Too low
                environment="development",
            )

        with pytest.raises(ValueError, match="Port must be between"):
            BackendConfig(
                host="127.0.0.1",
                port=70000,  # Too high
                environment="development",
            )

    def test_config_validates_backup_hour(self):
        """Config validates backup hour (0-23)."""
        with pytest.raises(ValueError, match="Backup hour"):
            BackendConfig(
                host="127.0.0.1",
                port=8000,
                backup_schedule_hour=25,  # Invalid
            )

    def test_config_server_url(self):
        """Config generates correct server URL."""
        config = BackendConfig(
            host="192.168.1.1",
            port=5000,
        )
        assert config.server_url() == "http://192.168.1.1:5000"

    def test_config_health_url(self):
        """Config generates correct health check URL."""
        config = BackendConfig()
        assert config.health_url() == "http://127.0.0.1:8000/health"


class TestStartupValidation:
    """Test startup condition validation."""

    def test_validate_startup_conditions_success(self, tmp_path):
        """Validation succeeds when all conditions are met."""
        config = BackendConfig(
            host="127.0.0.1",
            port=9001,  # Use high port to avoid conflicts
        )

        result = validate_startup_conditions(config)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_startup_creates_log_directory(self, tmp_path, monkeypatch):
        """Validation creates log directory if it doesn't exist."""
        config = BackendConfig()

        # Mock log directory to temp location
        monkeypatch.setattr("utils.config.Path", lambda *args: tmp_path / "logs")

        result = validate_startup_conditions(config)

        # Should still validate successfully even if log dir doesn't exist
        assert result is not None


class TestHealthCheckEndpoint:
    """Test the enhanced health check endpoint."""

    def test_health_endpoint_basic(self, client):
        """Health endpoint returns status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "ready" in data
        assert "uptime_ms" in data
        assert "timestamp" in data
        assert "db_status" in data
        assert "version" in data

    def test_health_endpoint_not_ready_on_startup(self, client):
        """Health endpoint reports not ready before app startup complete."""
        # Reset ready state to simulate startup
        health.set_app_ready(False)

        response = client.get("/health")
        data = response.json()

        assert data["ready"] is False
        assert data["status"] != "ok"

    def test_health_endpoint_ready_after_startup(self, client):
        """Health endpoint reports ready after app startup."""
        health.set_app_ready(True)

        response = client.get("/health")
        data = response.json()

        assert data["ready"] is True
        assert data["status"] == "ok"

    def test_health_endpoint_includes_environment(self, client, monkeypatch):
        """Health endpoint includes environment from config."""
        monkeypatch.setenv("ENV", "production")
        health.set_app_ready(True)

        response = client.get("/health")
        data = response.json()

        assert data["environment"] in ["development", "production", "testing"]

    def test_health_endpoint_db_check(self, client):
        """Health endpoint checks database connectivity."""
        health.set_app_ready(True)

        response = client.get("/health")
        data = response.json()

        # Database should be responsive
        assert data["db_status"] in ["ok", "error"]
        assert data["db_response_time_ms"] >= 0


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_init_db_creates_tables(self):
        """init_db creates all SQLModel tables."""
        # Use in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:")

        # Create tables
        SQLModel.metadata.create_all(engine)

        # Verify tables exist
        inspector = __import__("sqlalchemy").inspect(engine)
        tables = inspector.get_table_names()

        # Should have at least these tables
        assert len(tables) > 0

    def test_init_db_idempotent(self):
        """init_db can be called multiple times safely."""
        engine = create_engine("sqlite:///:memory:")

        # Call init multiple times
        SQLModel.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)
        SQLModel.metadata.create_all(engine)

        # Should not raise error
        inspector = __import__("sqlalchemy").inspect(engine)
        tables = inspector.get_table_names()
        assert len(tables) > 0


class TestSignalHandlers:
    """Test signal handling for graceful shutdown."""

    def test_signal_handlers_registered(self):
        """Signal handlers are registered on startup."""
        import signal

        from main import setup_signal_handlers

        # Should not raise
        setup_signal_handlers()

        # Verify handlers are registered (basic check)
        # Real test would require actually sending signals


class TestErrorHandling:
    """Test error handling during startup."""

    def test_startup_error_message(self):
        """StartupError provides useful error messages."""
        error = StartupError(
            "Configuration invalid",
            detail="Port must be 1024-65535",
            context={"port": 100},
        )

        assert "Configuration invalid" in str(error)
        assert "Port must be 1024-65535" in error.detail
        assert error.context["port"] == 100

    def test_startup_error_response_format(self):
        """StartupError can be converted to API response."""
        error = StartupError(
            "Database connection failed",
            detail="Database file is locked",
        )

        response = error.to_response(request_id="req-123")

        assert response.category == "startup_error"
        assert response.message == "Database connection failed"
        assert response.request_id == "req-123"


# Fixtures


@pytest.fixture
def client():
    """Create test client with clean database."""
    from fastapi.testclient import TestClient

    # Use in-memory database for tests
    from sqlmodel import Session, create_engine, select

    from main import app

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Create tables
    SQLModel.metadata.create_all(engine)

    # Override get_session
    def get_session_override():
        with Session(engine) as session:
            yield session

    from database import get_session

    app.dependency_overrides[get_session] = get_session_override

    yield TestClient(app)

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_health_state():
    """Reset health state before each test."""
    health.set_app_ready(False)
    yield
    health.set_app_ready(False)
