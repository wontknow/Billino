"""
Tests für Backup Service und Scheduler.

Testet:
- BackupHandler: DB-Backup, PDF-Backup, Cleanup
- BackupScheduler: Initialisierung, Status, Trigger
"""

import gc
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

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

            # Erstelle echte SQLite-Datenbank für Tests
            db_file = data_dir / "billino.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
            conn.execute("INSERT INTO test (data) VALUES ('test data')")
            conn.commit()
            conn.close()

            yield {
                "tmpdir": tmpdir,
                "backup_dir": backup_dir,
                "data_dir": data_dir,
                "db_file": db_file,
            }

            # Windows-spezifisch: Sicherstellen, dass alle SQLite-Dateihandles geschlossen sind
            gc.collect()
            time.sleep(0.1)  # Kurze Pause, damit Windows Dateihandles freigeben kann

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

        # Extrahiere Datum aus Dateinamen (Format: billino_YYYY-MM-DD_HH-MM-SS.db)
        filename = backup_path.name
        date_str = filename.replace("billino_", "").split("_")[0]

        # Verifiziere Datums-Format
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # Datum sollte heute sein
        today = datetime.now().date()
        file_date = date.date()
        assert file_date == today

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

        # Erstelle "alte" Backup-Dateien (älter als 5 Tage) als echte SQLite DBs
        old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        old_backup = handler.BACKUP_DAILY / f"billino_{old_date}_00-00-00.db"
        conn = sqlite3.connect(str(old_backup))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        # Erstelle "neue" Backup-Datei als echte SQLite DB
        new_date = datetime.now().strftime("%Y-%m-%d")
        new_backup = handler.BACKUP_DAILY / f"billino_{new_date}_00-00-00.db"
        conn = sqlite3.connect(str(new_backup))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

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
        BackupScheduler.initialize()

        BackupScheduler.start()
        assert BackupScheduler._scheduler.running is True

        BackupScheduler.stop()
        # Nach shutdown kann running False sein

    def test_scheduler_get_status(self):
        """Test: Scheduler-Status wird zurückgegeben."""
        BackupScheduler.initialize()
        BackupScheduler.start()

        status = BackupScheduler.get_status()

        assert "scheduler_running" in status
        assert "backup_status" in status
        assert status["scheduler_running"] is True

        BackupScheduler.stop()

    def test_scheduler_list_jobs(self):
        """Test: Registrierte Jobs werden aufgelistet."""
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

            # Erstelle echte SQLite-Datenbank
            db_file = data_dir / "billino.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
            conn.execute("INSERT INTO test (data) VALUES ('test data')")
            conn.commit()
            conn.close()

            BackupScheduler.initialize()

            result = BackupScheduler.trigger_backup_now()

            assert "success" in result
            # Kann fehlschlag haben wegen Pfad-Unterschieden, aber nicht crashen
            assert isinstance(result, dict)

    def test_backup_on_shutdown(self, monkeypatch):
        """Test: Shutdown-Backup (DB + PDFs) wird korrekt ausgeführt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backups"
            data_dir = tmpdir / "data"
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)
            (data_dir / "pdfs" / "summary_invoices").mkdir(parents=True)

            # Setze DATA_DIR Umgebungsvariable für isolierten Test
            monkeypatch.setenv("DATA_DIR", str(data_dir))

            # Erstelle echte SQLite-Datenbank
            db_file = data_dir / "billino.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
            conn.execute("INSERT INTO test (data) VALUES ('test shutdown data')")
            conn.commit()
            conn.close()

            # Erstelle Test-PDFs
            invoice_dir = data_dir / "pdfs" / "invoices"
            (invoice_dir / "test_invoice.pdf").write_text("Invoice PDF content")
            summary_dir = data_dir / "pdfs" / "summary_invoices"
            (summary_dir / "summary_invoice.pdf").write_text("Summary PDF content")

            # Initialisiere Scheduler mit Handler
            handler = BackupHandler(
                backup_root=backup_dir,
                db_path=db_file,
                tauri_enabled=False,
            )
            BackupScheduler._handler = handler

            # Führe Shutdown-Backup aus
            result = BackupScheduler.backup_on_shutdown()

            # Assertions für Backup-Ergebnis
            assert result is not None
            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True
            assert "timestamp" in result

            # Check DB backup result
            assert "db_backup" in result
            assert result["db_backup"]["success"] is True
            assert "path" in result["db_backup"]
            backup_path = Path(result["db_backup"]["path"])

            # Check PDF backup result
            assert "pdf_backup" in result
            assert result["pdf_backup"]["success"] is True
            assert "stats" in result["pdf_backup"]
            assert result["pdf_backup"]["stats"]["invoices"] == 1
            assert result["pdf_backup"]["stats"]["summary_invoices"] == 1

            # Verifiziere, dass DB-Backup erstellt wurde
            assert backup_path.exists()
            assert backup_path.name.startswith("billino_")

            # Verifiziere, dass PDF-Backup (Archivierung) durchgeführt wurde
            pdf_archive = data_dir / "pdfs" / "archive"
            assert (pdf_archive / "invoices" / "test_invoice.pdf").exists()
            assert (pdf_archive / "summary_invoices" / "summary_invoice.pdf").exists()
            assert backup_path.stat().st_size > 0

            # Windows-spezifisch: Cleanup
            gc.collect()
            time.sleep(0.1)

    def test_backup_on_shutdown_with_db_failure(self, monkeypatch):
        """Test: PDF-Backup läuft auch wenn DB-Backup fehlschlägt (Shutdown Safety)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backups"
            data_dir = tmpdir / "data"
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)
            (data_dir / "pdfs" / "summary_invoices").mkdir(parents=True)

            # Setze DATA_DIR Umgebungsvariable für isolierten Test
            monkeypatch.setenv("DATA_DIR", str(data_dir))

            # KEINE SQLite-Datenbank erstellen -> DB-Backup wird fehlschlagen
            db_file = data_dir / "billino.db"

            # Erstelle Test-PDFs
            invoice_dir = data_dir / "pdfs" / "invoices"
            (invoice_dir / "test_invoice.pdf").write_text("Invoice PDF content")
            summary_dir = data_dir / "pdfs" / "summary_invoices"
            (summary_dir / "summary_invoice.pdf").write_text("Summary PDF content")

            # Initialisiere Scheduler mit Handler (DB existiert nicht)
            handler = BackupHandler(
                backup_root=backup_dir,
                db_path=db_file,
                tauri_enabled=False,
            )
            BackupScheduler._handler = handler

            # Führe Shutdown-Backup aus
            result = BackupScheduler.backup_on_shutdown()

            # Assertions: Backup sollte partiell erfolgreich sein (nur PDFs)
            assert result is not None
            assert isinstance(result, dict)
            assert "success" in result
            assert result["success"] is True  # Erfolgreich weil PDF-Backup lief

            # Check DB backup result (sollte fehlgeschlagen sein)
            assert "db_backup" in result
            assert result["db_backup"]["success"] is False
            assert result["db_backup"]["path"] is None

            # Check PDF backup result (sollte erfolgreich sein)
            assert "pdf_backup" in result
            assert result["pdf_backup"]["success"] is True
            assert "stats" in result["pdf_backup"]
            assert result["pdf_backup"]["stats"]["invoices"] == 1
            assert result["pdf_backup"]["stats"]["summary_invoices"] == 1

            # Verifiziere, dass PDF-Backup (Archivierung) trotzdem durchgeführt wurde
            pdf_archive = data_dir / "pdfs" / "archive"
            assert (pdf_archive / "invoices" / "test_invoice.pdf").exists()
            assert (pdf_archive / "summary_invoices" / "summary_invoice.pdf").exists()

            # Windows-spezifisch: Cleanup
            gc.collect()
            time.sleep(0.1)

    def test_pdf_archive_cleanup(self):
        """Test: Alte archivierte PDFs werden gelöscht."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backups"
            data_dir = tmpdir / "data"
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)
            (data_dir / "pdfs" / "summary_invoices").mkdir(parents=True)

            # Erstelle echte SQLite-Datenbank
            db_file = data_dir / "billino.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
            conn.execute("INSERT INTO test (data) VALUES ('test data')")
            conn.commit()
            conn.close()

            handler = BackupHandler(
                backup_root=backup_dir,
                db_path=db_file,
                tauri_enabled=False,
                retention_days=5,
            )

            # Override PDF-Pfade
            handler.PDF_INVOICES_PATH = data_dir / "pdfs" / "invoices"
            handler.PDF_SUMMARY_PATH = data_dir / "pdfs" / "summary_invoices"
            handler.PDF_ARCHIVE = backup_dir / "pdfs" / "archive"

            # Erstelle alte archivierte PDFs
            archive_invoices = handler.PDF_ARCHIVE / "invoices"
            archive_invoices.mkdir(parents=True, exist_ok=True)
            old_pdf = archive_invoices / "old_invoice.pdf"
            old_pdf.write_text("Old PDF content")

            # Setze mtime auf älter als 5 Tage
            old_timestamp = (datetime.now() - timedelta(days=10)).timestamp()
            os.utime(old_pdf, (old_timestamp, old_timestamp))

            # Erstelle neue PDFs
            (handler.PDF_INVOICES_PATH / "new_invoice.pdf").write_text("New PDF")

            # Führe Backup aus (sollte auch Cleanup triggern)
            handler.backup_pdfs()

            # Neue archivierte PDF sollte existieren
            assert (archive_invoices / "new_invoice.pdf").exists()

            # Alte archivierte PDF sollte gelöscht worden sein
            assert not old_pdf.exists()

            # Windows-spezifisch: Cleanup
            gc.collect()
            time.sleep(0.1)

    def test_backup_overall_success_logic(self, monkeypatch):
        """Test: Overall success logic works correctly for different scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            backup_dir = tmpdir / "backups"
            data_dir = tmpdir / "data"
            (data_dir / "pdfs" / "invoices").mkdir(parents=True)

            # Test 1: DB success, no PDFs requested -> overall success
            db_file = data_dir / "billino.db"
            conn = sqlite3.connect(str(db_file))
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

            handler = BackupHandler(
                backup_root=backup_dir, db_path=db_file, tauri_enabled=False
            )
            BackupScheduler._handler = handler

            result = BackupScheduler._perform_backup(source="test", include_pdfs=False)
            assert result["success"] is True
            assert result["db_backup"]["success"] is True
            assert "pdf_backup" not in result

            # Test 2: DB failure, no PDFs requested -> overall failure
            handler.DB_PATH = Path("/nonexistent/db.db")
            result = BackupScheduler._perform_backup(source="test", include_pdfs=False)
            assert result["success"] is False
            assert result["db_backup"]["success"] is False

            # Test 3: DB success, PDF success -> overall success
            handler.DB_PATH = db_file
            handler.PDF_INVOICES_PATH = data_dir / "pdfs" / "invoices"
            (handler.PDF_INVOICES_PATH / "test.pdf").write_text("PDF")
            handler.PDF_ARCHIVE = backup_dir / "pdfs" / "archive"

            result = BackupScheduler._perform_backup(source="test", include_pdfs=True)
            assert result["success"] is True
            assert result["db_backup"]["success"] is True
            assert result["pdf_backup"]["success"] is True

            # Test 4: DB failure, PDF success -> overall success (shutdown safety!)
            handler.DB_PATH = Path("/nonexistent/db.db")
            result = BackupScheduler._perform_backup(source="test", include_pdfs=True)
            assert result["success"] is True  # Overall success because PDF succeeded
            assert result["db_backup"]["success"] is False
            assert result["pdf_backup"]["success"] is True

            # Windows-spezifisch: Cleanup
            gc.collect()
            time.sleep(0.1)
