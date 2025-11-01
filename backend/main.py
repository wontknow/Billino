# backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import init_db
from routers import customers, health, invoices, pdfs, profiles, summary_invoices


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (hier später evtl. cleanup, Logs, etc.)


app = FastAPI(
    title="Billino Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Router registrieren

app.include_router(health.router)
app.include_router(customers.router)
app.include_router(profiles.router)
app.include_router(invoices.router)
app.include_router(summary_invoices.router)
app.include_router(pdfs.router)
