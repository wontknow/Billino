# backend/main.py
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import customers, health, invoices, pdfs, profiles, summary_invoices
from utils import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (hier später evtl. cleanup, Logs, etc.)


# .env explizit aus dem Backend-Verzeichnis laden (robuster bei anderem Working Directory)
load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)

app = FastAPI(
    title="Billino Backend",
    version="0.1.0",
    lifespan=lifespan,
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
