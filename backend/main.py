# backend/main.py
import os
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()

    # Starte Backup-Scheduler (mit Konfiguration aus .env)
    backup_enabled = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
    if backup_enabled:
        backup_hour = int(os.getenv("BACKUP_SCHEDULE_HOUR", "2"))
        backup_minute = int(os.getenv("BACKUP_SCHEDULE_MINUTE", "0"))
        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        tauri_enabled = os.getenv("TAURI_ENABLED", "false").lower() == "true"

        BackupScheduler.initialize(
            backup_hour=backup_hour,
            backup_minute=backup_minute,
            retention_days=retention_days,
            tauri_enabled=tauri_enabled,
        )
        BackupScheduler.start()
        logger.info("✅ Backup-Scheduler gestartet")
    else:
        logger.info("⏸️ Backup-System deaktiviert (BACKUP_ENABLED=false)")

    yield

    # Shutdown
    BackupScheduler.stop()
    logger.info("✅ Backup-Scheduler gestoppt")


# .env explizit aus dem Backend-Verzeichnis laden (robuster bei anderem Working Directory)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

app = FastAPI(
    title="Billino Backend API",
    version="0.1.0",
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

# CORS – alles über .env steuern
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
