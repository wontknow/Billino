# Health router with enhanced status monitoring
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_engine, get_session
from utils import logger

router = APIRouter()

# Startup tracking
_start_time = time.time()
_is_ready = False


class HealthResponse(BaseModel):
    """Enhanced health check response with detailed status info."""

    status: str  # "ok" | "starting" | "degraded" | "error"
    ready: bool  # Backend ready for production traffic
    uptime_ms: int
    timestamp: str
    db_status: str  # "ok" | "locked" | "error"
    db_response_time_ms: int
    version: str
    environment: str


def set_app_ready(ready: bool) -> None:
    """Update app ready state (called by main.py on startup completion)."""
    global _is_ready
    _is_ready = ready


@router.get("/health", tags=["health"], response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Enhanced health check endpoint for Electron desktop integration.

    This endpoint serves as both a **Liveness Probe** (is the service running?)
    and **Readiness Probe** (is it ready for traffic?).

    **Returns:**
    - `status`: Overall health ("ok" if ready, else "starting"/"degraded"/"error")
    - `ready`: Whether the backend is accepting production traffic
    - `db_status`: Database connectivity status
    - `db_response_time_ms`: Round-trip time to database (timeout: 1000ms)

    **Status Meanings:**
    - `ok`: Fully operational, ready for traffic
    - `starting`: Initializing, health checks in progress
    - `degraded`: Running but experiencing issues (DB slow, etc)
    - `error`: Critical failure, not operational

    **Example Response:**
    ```json
    {
        "status": "ok",
        "ready": true,
        "uptime_ms": 5432,
        "timestamp": "2025-01-01T12:00:00.000000",
        "db_status": "ok",
        "db_response_time_ms": 2,
        "version": "0.1.0",
        "environment": "production"
    }
    ```

    **Used by Electron to:**
    1. Detect when backend has fully started
    2. Monitor health during application runtime
    3. Trigger alerts if degraded
    """
    import os

    logger.debug("🏥 Health check requested")

    start = time.time()
    db_status = "ok"
    db_response_time = 0

    # Quick database connectivity check (timeout: 1000ms)
    try:
        # Use a simple query to test connectivity
        session: Session = next(get_session())
        try:
            # Execute minimal query (just validates connection)
            session.execute(select(1))
            db_response_time = int((time.time() - start) * 1000)
        finally:
            session.close()

    except Exception as e:
        db_status = "error"
        db_response_time = int((time.time() - start) * 1000)
        logger.error(f"❌ Database health check failed: {e}")

    # Determine overall status
    status = "ok" if (_is_ready and db_status == "ok") else "starting"
    if db_status == "error":
        status = "degraded" if _is_ready else "error"

    uptime_ms = int((time.time() - _start_time) * 1000)

    return HealthResponse(
        status=status,
        ready=_is_ready,
        uptime_ms=uptime_ms,
        timestamp=datetime.now().isoformat(),
        db_status=db_status,
        db_response_time_ms=db_response_time,
        version="0.1.0",
        environment=os.getenv("ENV", "development"),
    )
