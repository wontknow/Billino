from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional

from sqlmodel import Session, SQLModel, create_engine

# Datenbank im data/ Ordner
_DB_DIR = Path(__file__).resolve().parent / "data"
_DB_FILE = _DB_DIR / "billino.db"


def _build_sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def get_db_url() -> str:
    """Erlaube Override via Env (BILLINO_DB_URL), sonst lokale Datei."""
    env_url = os.getenv("BILLINO_DB_URL")
    if env_url:
        return env_url
    return _build_sqlite_url(_DB_FILE)


_engine = None  # lazy Singleton


def get_engine(url: Optional[str] = None):
    """Erzeuge/merke Engine (keine Nebenwirkungen außerhalb dieses Moduls)."""
    global _engine
    if url is None:
        url = get_db_url()
    if _engine is None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
    return _engine


def init_db(engine=None) -> None:
    """Erzeuge Tabellen gemäß SQLModel-Metadaten."""
    # Stelle sicher, dass data/ Verzeichnis existiert
    _DB_DIR.mkdir(parents=True, exist_ok=True)

    if engine is None:
        engine = get_engine()
    import models

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI-Dependency: liefert eine Session pro Request."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
