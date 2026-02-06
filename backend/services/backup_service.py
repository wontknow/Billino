"""
Backup Service für Datenbanken und PDFs.

Unterstützt zwei Modi:
1. Desktop: Electron Desktop-App Backups (nutzt AppData/Roaming)
2. Basic: Einfache Datei-basierte Backups im Backend-Ordner
"""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from database import get_data_dir
from utils.logger import logger

# Backend-Root Verzeichnis (wo main.py liegt)
BACKEND_ROOT = Path(__file__).parent.parent


def get_backup_paths():
    """
    Gibt Backup-Pfade zurück (respektiert DATA_DIR).

    - Electron Desktop-App: AppData/Roaming/Billino/backups/
    - Standalone FE/BE: backend/data/backups/
    """
    data_dir = get_data_dir()
    return {
        "backup_root": data_dir / "backups",
        "backup_daily": data_dir / "backups" / "daily",
        "pdf_archive": data_dir / "pdfs" / "archive",
        "pdf_invoices": data_dir / "pdfs" / "invoices",
        "pdf_summary": data_dir / "pdfs" / "summary_invoices",
    }


class BackupHandler:
    """
    Zentrale Backup-Handler Klasse für DB und PDFs.

    Erkennt automatisch Desktop-Umgebung (Electron) und wählt entsprechende Backup-Strategie.
    """

    def __init__(
        self,
        backup_root: Optional[Path] = None,
        db_path: Optional[Path] = None,
        desktop_enabled: bool = False,
        retention_days: int = 30,
    ):
        """
        Initialisiere BackupHandler.

        Args:
            backup_root: Root-Verzeichnis für Backups (standard: get_backup_paths())
            db_path: Pfad zur Datenbank (standard: get_db_file())
            desktop_enabled: Desktop-Modus aktiviert / Electron (default: False)
            retention_days: Tage, bis alte Backups gelöscht werden (default: 30)
        """
        from database import get_db_file

        paths = get_backup_paths()

        self.BACKUP_ROOT = backup_root or paths["backup_root"]
        self.BACKUP_DAILY = self.BACKUP_ROOT / "daily"
        self.PDF_ARCHIVE = paths["pdf_archive"]
        self.DB_PATH = db_path or get_db_file()
        self.PDF_INVOICES_PATH = paths["pdf_invoices"]
        self.PDF_SUMMARY_PATH = paths["pdf_summary"]

        self.desktop_enabled = self._detect_desktop_enabled(desktop_enabled)
        self.retention_days = retention_days

        # Erstelle Backup-Verzeichnisse, falls nicht vorhanden
        self._ensure_backup_directories()

    @staticmethod
    def _detect_desktop_enabled(desktop_enabled: bool) -> bool:
        """
        Erkenne Desktop-Umgebung (Electron) automatisch.

        Prüft auf:
        - DESKTOP_ENABLED Umgebungsvariable
        - APP_ENV=desktop Umgebungsvariable

        Args:
            desktop_enabled: Explizit gesetzter Wert (überschreibt Auto-Detection)

        Returns:
            True wenn Desktop-Modus aktiviert ist, sonst False
        """
        # Expliziter Wert hat Vorrang
        if desktop_enabled:
            return True

        # Auto-Detection über Umgebungsvariable
        env_desktop = os.getenv("DESKTOP_ENABLED", "false").lower()
        if env_desktop == "true":
            logger.info("🖥️ Desktop-Modus erkannt (Umgebungsvariable)")
            return True

        # Electron setzt APP_ENV=desktop
        if os.getenv("APP_ENV", "").lower() == "desktop":
            logger.info("🖥️ Desktop-Modus erkannt (APP_ENV=desktop)")
            return True

        logger.info("💾 Basic-Modus aktiviert (lokal, dateibasiert)")
        return False

    def _ensure_backup_directories(self) -> None:
        """Erstelle Backup-Verzeichnisse, falls nicht vorhanden."""
        try:
            self.BACKUP_DAILY.mkdir(parents=True, exist_ok=True)
            self.PDF_ARCHIVE.mkdir(parents=True, exist_ok=True)
            logger.debug(
                f"Backup-Verzeichnisse erstellt/verifiziert: {self.BACKUP_ROOT}"
            )
            logger.debug(f"DB-Pfad: {self.DB_PATH}")
            logger.debug(f"PDF-Archiv: {self.PDF_ARCHIVE}")
        except OSError as e:
            logger.error(f"Fehler beim Erstellen von Backup-Verzeichnissen: {e}")
            raise

    def backup_database(self) -> Optional[Path]:
        """
        Erstelle ein Backup der Datenbank.

        Format: billino_YYYY-MM-DD_HH-MM-SS.db
        Speicherort: backups/daily/

        Returns:
            Pfad zur erstellten Backup-Datei, None bei Fehler
        """
        if not self.DB_PATH.exists():
            logger.warning(f"⚠️ Datenbank nicht gefunden: {self.DB_PATH}")
            return None

        # Zeitstempel für Backup-Dateiname (mit Uhrzeit für Eindeutigkeit)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"billino_{timestamp}.db"
        backup_path = self.BACKUP_DAILY / backup_filename

        try:
            # Verwende SQLite Backup API statt shutil.copy2
            # Öffne Quell- und Zieldatenbank in Context Managern,
            # damit Verbindungen auch bei Fehlern sicher geschlossen werden
            with sqlite3.connect(str(self.DB_PATH)) as source_conn:
                with sqlite3.connect(str(backup_path)) as dest_conn:
                    # Führe Backup durch (sicher auch bei aktiver Datenbank)
                    with dest_conn:
                        source_conn.backup(dest_conn)
            logger.info(f"✅ Datenbank-Backup erstellt: {backup_path}")

            # Cleanup alte Backups
            self._cleanup_old_backups()

            return backup_path
        except (IOError, OSError, sqlite3.Error) as e:
            logger.error(f"❌ Fehler beim DB-Backup: {e}")
            return None

    def backup_pdfs(self) -> dict[str, int]:
        """
        Backup PDFs in Archive-Verzeichnis (Redundanz).

        Kopiert PDF-Dateien in Spiegelstruktur:
        - data/pdfs/invoices/ → data/pdfs/archive/invoices/
        - data/pdfs/summary_invoices/ → data/pdfs/archive/summary_invoices/

        Returns:
            Dict mit Statistiken: {"invoices": count, "summary_invoices": count}
        """
        stats = {"invoices": 0, "summary_invoices": 0}

        # Backup Invoices
        if self.PDF_INVOICES_PATH.exists():
            try:
                archive_invoices = self.PDF_ARCHIVE / "invoices"
                archive_invoices.mkdir(parents=True, exist_ok=True)

                for pdf_file in self.PDF_INVOICES_PATH.glob("*.pdf"):
                    shutil.copy2(pdf_file, archive_invoices / pdf_file.name)
                    stats["invoices"] += 1

                logger.debug(f"✅ {stats['invoices']} Invoice-PDFs archiviert")
            except (IOError, OSError) as e:
                logger.error(f"❌ Fehler beim Backup von Invoice-PDFs: {e}")

        # Backup Summary Invoices
        if self.PDF_SUMMARY_PATH.exists():
            try:
                archive_summary = self.PDF_ARCHIVE / "summary_invoices"
                archive_summary.mkdir(parents=True, exist_ok=True)

                for pdf_file in self.PDF_SUMMARY_PATH.glob("*.pdf"):
                    shutil.copy2(pdf_file, archive_summary / pdf_file.name)
                    stats["summary_invoices"] += 1

                logger.debug(
                    f"✅ {stats['summary_invoices']} Summary Invoice-PDFs archiviert"
                )
            except (IOError, OSError) as e:
                logger.error(f"❌ Fehler beim Backup von Summary Invoice-PDFs: {e}")

        if stats["invoices"] > 0 or stats["summary_invoices"] > 0:
            logger.info(f"✅ PDF-Backup abgeschlossen: {sum(stats.values())} Dateien")

        return stats

    def _cleanup_old_backups(self) -> None:
        """
        Lösche Backup-Dateien älter als `retention_days`.

        Nur Dateien im Format `billino_YYYY-MM-DD*.db` werden gelöscht.
        """
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0

        try:
            for backup_file in self.BACKUP_DAILY.glob("billino_*.db"):
                # Parse Datum aus Dateinamen
                try:
                    # Extrahiere nur das Datum (YYYY-MM-DD Teil)
                    date_str = backup_file.stem.replace("billino_", "").split("_")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"🗑️ Altes Backup gelöscht: {backup_file.name}")
                except (ValueError, IndexError):
                    # Dateinamen-Format passt nicht, überspringen
                    continue

            if deleted_count > 0:
                logger.info(
                    f"✅ {deleted_count} alte Backups gelöscht (älter als {self.retention_days} Tage)"
                )
        except OSError as e:
            logger.error(f"❌ Fehler beim Löschen alter Backups: {e}")

    def get_backup_status(self) -> dict:
        """
        Hole Status der letzten Backups.

        Returns:
            Dict mit:
            - last_db_backup: Datum/Zeit des letzten DB-Backups oder None
            - backup_count: Anzahl vorhandener Backups
            - desktop_enabled: Boolean ob Desktop-Modus (Electron) aktiv ist
            - backup_path: Pfad zum Backup-Verzeichnis
        """
        backup_files = sorted(self.BACKUP_DAILY.glob("billino_*.db"), reverse=True)

        last_backup = None
        if backup_files:
            last_backup = backup_files[0].stat().st_mtime

        return {
            "last_db_backup": last_backup,
            "backup_count": len(backup_files),
            "desktop_enabled": self.desktop_enabled,
            "backup_path": str(self.BACKUP_DAILY),
            "retention_days": self.retention_days,
        }

    def list_backups(self) -> list[dict]:
        """
        Liste alle verfügbaren Backups auf.

        Returns:
            Liste von Dicts mit: filename, path, size_bytes, created_timestamp
        """
        backups = []

        try:
            for backup_file in sorted(
                self.BACKUP_DAILY.glob("billino_*.db"), reverse=True
            ):
                stat = backup_file.stat()
                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "size_bytes": stat.st_size,
                        "created_timestamp": stat.st_mtime,
                        "created_iso": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                    }
                )
        except OSError as e:
            logger.error(f"❌ Fehler beim Auflisten von Backups: {e}")

        return backups

    def verify_backup(self, backup_path: Path) -> bool:
        """
        Verifiziere ein Backup-Datei auf Integrität.

        Checks:
        - Datei existiert
        - Datei > 0 bytes
        - Datei ist lesbar

        Args:
            backup_path: Pfad zur Backup-Datei

        Returns:
            True wenn Backup OK, False sonst
        """
        if not backup_path.exists():
            logger.error(f"❌ Backup nicht gefunden: {backup_path}")
            return False

        if backup_path.stat().st_size == 0:
            logger.error(f"❌ Backup ist leer: {backup_path}")
            return False

        if not os.access(backup_path, os.R_OK):
            logger.error(f"❌ Backup ist nicht lesbar: {backup_path}")
            return False

        logger.info(f"✅ Backup verifiziert: {backup_path}")
        return True
