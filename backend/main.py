# backend/main.py
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import customers, health, invoices, pdfs, profiles, summary_invoices


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (hier später evtl. cleanup, Logs, etc.)


load_dotenv()

app = FastAPI(
    title="Billino Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware konfigurieren
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not origins or origins == [""]:
    origins = ["http://localhost:3000", "tauri://localhost"]

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
