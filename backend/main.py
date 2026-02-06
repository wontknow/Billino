# backend/main.py
"""
Billino Invoice Management API - Main FastAPI Application

This module initializes and configures the FastAPI application with:
- Database initialization and connection pooling
- CORS middleware for cross-origin requests
- Graceful startup/shutdown lifecycle
- Background services (backup scheduler, PDF generation)
- Enhanced health checking for Electron desktop integration
"""

import os
import signal
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import (
    backups,
    customers,
    health,
    invoices,
    pdfs,
    profiles,
    summary_invoices,
)
from services.backup_scheduler import BackupScheduler
from utils import logger
from utils.config import BackendConfig, validate_startup_conditions
from utils.errors import StartupError


def setup_signal_handlers() -> None:
    """
    Register OS signal handlers for graceful shutdown.

    Registers handlers for SIGTERM and SIGINT to ensure the application
    can be terminated cleanly by the desktop environment (Electron) or by
    system signals, triggering the FastAPI lifespan shutdown sequence.
    """

    def signal_handler(sig, frame):
        signal_name = "SIGTERM" if sig == signal.SIGTERM else "SIGINT"
        logger.warning(f"⚠️ Received {signal_name}, initiating graceful shutdown...")
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("✅ Signal handlers registered (SIGTERM, SIGINT)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown.

    **Startup Sequence:**
    1. Load and validate configuration
    2. Check startup conditions (port availability, paths, etc.)
    3. Initialize database and create tables
    4. Configure and start backup scheduler
    5. Mark app as ready (health endpoint returns ready=true)

    **Shutdown Sequence:**
    1. Mark app as not ready (health endpoint returns ready=false)
    2. Stop backup scheduler and flush pending operations
    3. Close database connections

    Raises:
        StartupError: If critical startup conditions are not met
    """
    logger.info("=" * 60)
    logger.info("🚀 Backend startup sequence initiated...")
    logger.info("=" * 60)

    try:
        # Load and validate configuration
        logger.info("⚙️ Loading configuration...")
        try:
            config = BackendConfig.from_env()
            logger.info(f"✅ Configuration loaded: {config.server_url()}")
        except ValueError as e:
            raise StartupError(
                "Invalid backend configuration",
                detail=str(e),
                context={"variable": str(e)},
            )

        # Validate startup conditions
        logger.info("🔍 Validating startup conditions...")
        validation = validate_startup_conditions(config)
        if not validation["valid"]:
            errors = "\n  - ".join(validation["errors"])
            raise StartupError(
                "Startup validation failed",
                detail=errors,
                context={"errors": validation["errors"]},
            )
        if validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(warning)
        logger.info("✅ Startup conditions validated")

        # Database initialization
        logger.info("📊 Initializing database...")
        init_db()
        logger.info("✅ Database initialized")

        # Backup Scheduler initialization
        if config.backup_enabled:
            try:
                logger.info(
                    f"⏰ Configuring backup scheduler: "
                    f"Daily at {config.backup_schedule_hour:02d}:{config.backup_schedule_minute:02d} "
                    f"(retention: {config.backup_retention_days} days)"
                )

                BackupScheduler.initialize(
                    backup_hour=config.backup_schedule_hour,
                    backup_minute=config.backup_schedule_minute,
                    retention_days=config.backup_retention_days,
                    desktop_enabled=config.desktop_enabled,
                )
                BackupScheduler.start()
                logger.info("✅ Backup-Scheduler started")
            except Exception as e:
                logger.warning(
                    f"⚠️ Backup scheduler initialization failed: {e}. "
                    "Continuing without automated backups."
                )
        else:
            logger.info("⏸️ Backup system disabled (BACKUP_ENABLED=false)")

        # Mark app as ready (important for Electron health checks)
        health.set_app_ready(True)
        logger.info("=" * 60)
        logger.info("✅ Backend fully operational and ready for traffic!")
        logger.info("=" * 60)

    except StartupError as e:
        logger.error(f"❌ Startup failed: {e}")
        health.set_app_ready(False)
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during startup: {e}", exc_info=True)
        health.set_app_ready(False)
        raise StartupError(
            "Unexpected startup error",
            detail=str(e),
        )

    yield

    # Shutdown sequence
    logger.info("=" * 60)
    logger.info("🛑 Backend shutdown sequence initiated...")
    logger.info("=" * 60)

    # Mark app as not ready immediately to reject new requests
    health.set_app_ready(False)
    logger.info("📊 App marked as not ready (rejecting new requests)")

    try:
        if BackupScheduler._scheduler is not None:
            logger.info("⏳ Stopping backup scheduler...")
            BackupScheduler.stop()
            logger.info("✅ Backup scheduler stopped")

        logger.info("=" * 60)
        logger.info("✅ Backend shutdown complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}", exc_info=True)


# .env explizit aus dem Backend-Verzeichnis laden (robuster bei anderem Working Directory)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

app = FastAPI(
    title="Billino Backend API",
    version="2.0.0",
    description="""
# Billino Invoice Management API

A REST API for managing invoices, customers, and profiles with PDF generation capabilities.

## Features

- **Customer Management**: Create, read, update, and search customers
- **Profile Management**: Manage seller/company profiles with tax settings
- **Invoice Management**: Create invoices with automatic number generation, line items, and tax calculations
- **Summary Invoices**: Combine multiple invoices into summary documents (Sammelrechnungen)
- **PDF Generation**: Generate and store PDF representations of invoices in multiple formats
- **Tax Compliance**: German tax law compliance (VAT handling per §19 UStG)

## API Structure

The API is organized into the following resource groups:

### Health Check (`/health`)
System health and status monitoring

### Customers (`/customers`)
Manage invoice recipients and customer information

### Profiles (`/profiles`)
Manage seller/company profiles with tax settings and bank information

### Invoices (`/invoices`)
Create and manage individual invoices with line items

### Summary Invoices (`/summary-invoices`)
Combine multiple invoices into summary documents

### PDFs (`/pdfs`)
Generate and manage PDF representations of invoices

## Key Concepts

- **Invoice Numbers**: Automatically generated globally in format "YY | NNN" (e.g., "25 | 001")
- **Tax Handling**: Supports both gross and net amounts with configurable tax rates
- **VAT Compliance**: Full support for German VAT law (§19 UStG exemption)
- **Base64 PDFs**: All PDFs are returned as base64-encoded content for easy transmission

## Authentication

Currently, the API has no authentication. CORS is configured via environment variables.

## Error Handling

The API returns standard HTTP status codes:
- `200/201`: Success
- `400`: Bad request (validation errors)
- `404`: Not found
- `422`: Validation error (unprocessable entity)

See the individual endpoint documentation for specific error responses.
    """,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "customers", "description": "Manage customers/invoice recipients"},
        {
            "name": "profiles",
            "description": "Manage seller/company profiles with tax settings",
        },
        {"name": "invoices", "description": "Create and manage individual invoices"},
        {
            "name": "summary_invoices",
            "description": "Create and manage summary invoices (Sammelrechnungen)",
        },
        {
            "name": "PDFs",
            "description": "Generate and manage PDF representations of invoices",
        },
        {
            "name": "backups",
            "description": "Database and file backup management",
        },
    ],
)

# CORS – configuration loaded from environment via BackendConfig
# (origins are loaded during lifespan startup and applied via middleware)
origins = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
]
logger.info(f"[CORS] Allowed origins: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registrieren
app.include_router(health.router)
app.include_router(customers.router)
app.include_router(profiles.router)
app.include_router(invoices.router)
app.include_router(summary_invoices.router)
app.include_router(pdfs.router)
app.include_router(backups.router)


if __name__ == "__main__":
    """
    Entry point for the Billino backend server.

    This is used when running the backend standalone or from Electron.
    - Registers OS signal handlers for graceful shutdown
    - Starts uvicorn server on the configured host:port
    - Host and port are configurable via environment variables
    """
    import socket

    import uvicorn

    # Setup signal handlers before starting the server
    setup_signal_handlers()

    # Get server configuration from environment
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    env = os.getenv("ENV", "development")
    reload = env == "development"

    logger.info(f"🌐 Starting Billino backend on {host}:{port} (environment: {env})")

    # Create a socket with SO_REUSEADDR to allow binding after recent closes
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.close()

    try:
        if reload:
            # Use import string for reload mode
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                reload=True,
                log_config=None,  # Use our custom logger
            )
        else:
            # Use app instance for production
            uvicorn.run(
                app,
                host=host,
                port=port,
                reload=False,
                log_config=None,  # Use our custom logger
            )
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted by user")
