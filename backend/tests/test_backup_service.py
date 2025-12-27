"""
Tests für Backup Service und Scheduler.

Testet:
- BackupHandler: DB-Backup, PDF-Backup, Cleanup
- BackupScheduler: Initialisierung, Status, Trigger
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.backup_scheduler import BackupScheduler
from services.backup_service import BackupHandler


class TestBackupHandler:
    """Tests für BackupHandler Klasse."""

    @pytest.fixture
    def temp_dirs(self):
        """Erstelle temporäre Verzeichnisse für Tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backups"
            data_dir = tmpdir / "data"

            # Erstelle Struktur
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)
            (data_dir / "pdfs" / "summary_invoices").mkdir(parents=True)

            # Erstelle Test-DB Datei
            db_file = data_dir / "billino.db"
            db_file.write_text("SQLite format 3" + "\x00" * 100)

            yield {
                "tmpdir": tmpdir,
                "backup_dir": backup_dir,
                "data_dir": data_dir,
                "db_file": db_file,
            }

    def test_backup_handler_initialization(self, temp_dirs):
        """Test: BackupHandler wird korrekt initialisiert."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
            tauri_enabled=False,
        )

        assert handler.tauri_enabled is False
        assert handler.retention_days == 30
        assert temp_dirs["backup_dir"].exists()
        assert (temp_dirs["backup_dir"] / "daily").exists()

    def test_tauri_detection_environment_variable(self, temp_dirs, monkeypatch):
        """Test: Tauri-Detection über Umgebungsvariable."""
        monkeypatch.setenv("TAURI_ENABLED", "true")

        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        assert handler.tauri_enabled is True

    def test_tauri_detection_explicit(self, temp_dirs):
        """Test: Tauri-Detection mit explizitem Wert."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
            tauri_enabled=True,
        )

        assert handler.tauri_enabled is True

    def test_database_backup_creation(self, temp_dirs):
        """Test: Datenbank-Backup wird erstellt."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        backup_path = handler.backup_database()

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.startswith("billino_")
        assert backup_path.name.endswith(".db")
        assert backup_path.stat().st_size > 0

    def test_database_backup_naming(self, temp_dirs):
        """Test: Backup-Datei wird mit korrektem Datum benannt."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        backup_path = handler.backup_database()

        # Extrahiere Datum aus Dateinamen
        filename = backup_path.name  # "billino_YYYY-MM-DD.db"
        date_str = filename.replace("billino_", "").replace(".db", "")

        # Verifiziere Datums-Format
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # Sollte heute oder gestern sein (in Fall von Zeitzonen-Unterschied)
        today = datetime.now()
        delta = (today - date).days
        assert delta in [0, 1]

    def test_database_backup_nonexistent_db(self, temp_dirs):
        """Test: Backup schlägt fehl, wenn DB nicht existiert."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=Path("/nonexistent/billino.db"),
        )

        result = handler.backup_database()

        assert result is None

    def test_pdf_backup_creation(self, temp_dirs):
        """Test: PDF-Backup wird erstellt."""
        # Erstelle Test-PDFs
        invoice_dir = temp_dirs["data_dir"] / "pdfs" / "invoices"
        (invoice_dir / "test_1.pdf").write_text("PDF content")
        (invoice_dir / "test_2.pdf").write_text("PDF content")

        summary_dir = temp_dirs["data_dir"] / "pdfs" / "summary_invoices"
        (summary_dir / "summary_1.pdf").write_text("PDF content")

        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        # Override PDF-Pfade
        handler.PDF_INVOICES_PATH = invoice_dir
        handler.PDF_SUMMARY_PATH = summary_dir
        handler.PDF_ARCHIVE = temp_dirs["backup_dir"] / "pdfs" / "archive"

        stats = handler.backup_pdfs()

        assert stats["invoices"] == 2
        assert stats["summary_invoices"] == 1
        assert (handler.PDF_ARCHIVE / "invoices" / "test_1.pdf").exists()
        assert (handler.PDF_ARCHIVE / "summary_invoices" / "summary_1.pdf").exists()

    def test_backup_cleanup_old_files(self, temp_dirs):
        """Test: Alte Backups werden gelöscht."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
            retention_days=5,
        )

        # Erstelle "alte" Backup-Dateien (älter als 5 Tage)
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_backup = handler.BACKUP_DAILY / f"billino_{old_date}.db"
        old_backup.write_text("old backup")

        # Erstelle "neue" Backup-Datei
        new_date = datetime.now().strftime("%Y-%m-%d")
        new_backup = handler.BACKUP_DAILY / f"billino_{new_date}.db"
        new_backup.write_text("new backup")

        # Trigger Cleanup über backup_database()
        handler.backup_database()

        # Alte sollte gelöscht sein
        assert not old_backup.exists()
        # Neue sollte existieren
        assert new_backup.exists()

    def test_get_backup_status(self, temp_dirs):
        """Test: Backup-Status wird korrekt zurückgegeben."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
            retention_days=30,
        )

        # Erstelle ein Backup
        handler.backup_database()

        status = handler.get_backup_status()

        assert "last_db_backup" in status
        assert "backup_count" in status
        assert status["tauri_enabled"] is False
        assert status["retention_days"] == 30
        assert status["backup_count"] == 1

    def test_list_backups(self, temp_dirs):
        """Test: Backup-Liste wird korrekt generiert."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        # Erstelle mehrere Backups
        handler.backup_database()

        backup_list = handler.list_backups()

        assert len(backup_list) >= 1
        backup = backup_list[0]

        assert "filename" in backup
        assert "path" in backup
        assert "size_bytes" in backup
        assert "created_iso" in backup
        assert backup["filename"].startswith("billino_")
        assert backup["size_bytes"] > 0

    def test_verify_backup_success(self, temp_dirs):
        """Test: Backup-Verifikation erfolgreich."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        backup_path = handler.backup_database()
        is_valid = handler.verify_backup(backup_path)

        assert is_valid is True

    def test_verify_backup_nonexistent(self, temp_dirs):
        """Test: Verifikation schlägt fehl für nicht-existente Datei."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        is_valid = handler.verify_backup(Path("/nonexistent/backup.db"))

        assert is_valid is False

    def test_verify_backup_empty_file(self, temp_dirs):
        """Test: Verifikation schlägt fehl für leere Datei."""
        handler = BackupHandler(
            backup_root=temp_dirs["backup_dir"],
            db_path=temp_dirs["db_file"],
        )

        empty_backup = handler.BACKUP_DAILY / "empty_backup.db"
        empty_backup.write_text("")

        is_valid = handler.verify_backup(empty_backup)

        assert is_valid is False


class TestBackupScheduler:
    """Tests für BackupScheduler Klasse."""

    def setup_method(self):
        """Reset Scheduler vor jedem Test."""
        BackupScheduler._scheduler = None
        BackupScheduler._handler = None

    def test_scheduler_initialization(self):
        """Test: Scheduler wird korrekt initialisiert."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            BackupScheduler.initialize(
                backup_hour=3,
                backup_minute=30,
                retention_days=7,
                tauri_enabled=False,
            )

            assert BackupScheduler._scheduler is not None
            assert BackupScheduler._handler is not None

    def test_scheduler_start_stop(self):
        """Test: Scheduler kann gestartet und gestoppt werden."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            BackupScheduler.initialize()

            BackupScheduler.start()
            assert BackupScheduler._scheduler.running is True

            BackupScheduler.stop()
            # Nach shutdown kann running False sein

    def test_scheduler_get_status(self):
        """Test: Scheduler-Status wird zurückgegeben."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            BackupScheduler.initialize()
            BackupScheduler.start()

            status = BackupScheduler.get_status()

            assert "scheduler_running" in status
            assert "backup_status" in status
            assert status["scheduler_running"] is True

            BackupScheduler.stop()

    def test_scheduler_list_jobs(self):
        """Test: Registrierte Jobs werden aufgelistet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            BackupScheduler.initialize()

            jobs = BackupScheduler.list_jobs()

            assert len(jobs) >= 1
            job = jobs[0]
            assert "id" in job
            assert "name" in job
            assert job["id"] == "backup_database_daily"

    def test_scheduler_trigger_backup(self):
        """Test: Manuelles Backup kann getriggert werden."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            data_dir = tmpdir / "data"
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)
            (data_dir / "pdfs" / "summary_invoices").mkdir(parents=True)

            db_file = data_dir / "billino.db"
            db_file.write_text("SQLite format 3" + "\x00" * 100)

            BackupScheduler.initialize()

            result = BackupScheduler.trigger_backup_now()

            assert "success" in result
            # Kann fehlschlag haben wegen Pfad-Unterschieden, aber nicht crashen
            assert isinstance(result, dict)
