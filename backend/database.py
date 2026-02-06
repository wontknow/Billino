from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional

from sqlmodel import Session, SQLModel, create_engine

# Default: Datenbank im data/ Ordner (für standalone FE/BE)
_DEFAULT_DB_DIR = Path(__file__).resolve().parent / "data"
_DEFAULT_DB_FILE = _DEFAULT_DB_DIR / "billino.db"


def get_data_dir() -> Path:
    """
    Gibt das Daten-Verzeichnis zurück.

    - Electron Desktop-App: Nutzt DATA_DIR Umgebungsvariable (AppData/Roaming)
    - Standalone FE/BE: Nutzt backend/data/ (default)
    """
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        path = Path(data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # Default: backend/data/
    _DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_DB_DIR


def get_db_file() -> Path:
    """Gibt den Datenbank-Pfad zurück (respektiert DATA_DIR)."""
    return get_data_dir() / "billino.db"


def _build_sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path}"


def get_db_url() -> str:
    """Erlaube Override via Env (BILLINO_DB_URL), sonst nutze get_db_file()."""
    env_url = os.getenv("BILLINO_DB_URL")
    if env_url:
        return env_url
    return _build_sqlite_url(get_db_file())


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
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    if engine is None:
        engine = get_engine()
    import models

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI-Dependency: liefert eine Session pro Request."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
