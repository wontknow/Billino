"""
Scheduler für periodische Backup-Jobs.

Nutzt APScheduler für tägliche Backups und Cleanup-Tasks.
"""

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from services.backup_service import BackupHandler
from utils.logger import logger


class BackupScheduler:
    """
    Verwaltet periodische Backup-Jobs mit APScheduler.

    Standardkonfiguration:
    - Tägliches Backup um 02:00 UTC
    - Retention: 30 Tage
    """

    _scheduler: Optional[BackgroundScheduler] = None
    _handler: Optional[BackupHandler] = None

    @classmethod
    def initialize(
        cls,
        backup_hour: int = 2,
        backup_minute: int = 0,
        retention_days: int = 30,
        tauri_enabled: bool = False,
    ) -> None:
        """
        Initialisiere Scheduler mit Konfiguration.

        Args:
            backup_hour: Stunde für tägliches Backup (UTC, default: 2)
            backup_minute: Minute für tägliches Backup (default: 0)
            retention_days: Tage, bis alte Backups gelöscht werden (default: 30)
            tauri_enabled: Tauri-Modus (default: False)
        """
        if cls._scheduler is not None:
            logger.warning("⚠️ Scheduler bereits initialisiert, ignoriere Init")
            return

        # Erstelle BackupHandler
        cls._handler = BackupHandler(
            tauri_enabled=tauri_enabled,
            retention_days=retention_days,
        )

        # Erstelle und starte Scheduler
        cls._scheduler = BackgroundScheduler(daemon=True)

        # Registriere Backup-Job
        cls._scheduler.add_job(
            func=cls._run_backup,
            trigger=CronTrigger(hour=backup_hour, minute=backup_minute),
            id="backup_database_daily",
            name="Tägliches Datenbank-Backup",
            replace_existing=True,
            misfire_grace_time=300,  # 5 Min Toleranz für verpasste Jobs
        )

        logger.info(
            f"✅ Backup-Scheduler initialisiert: "
            f"täglich um {backup_hour:02d}:{backup_minute:02d} UTC"
        )

    @classmethod
    def start(cls) -> None:
        """Starte den Scheduler."""
        if cls._scheduler is None:
            logger.error("❌ Scheduler nicht initialisiert, starte zuerst initialize()")
            return

        if cls._scheduler.running:
            logger.warning("⚠️ Scheduler läuft bereits")
            return

        cls._scheduler.start()
        logger.info("✅ Backup-Scheduler gestartet")

    @classmethod
    def stop(cls) -> None:
        """Stoppe den Scheduler."""
        if cls._scheduler is None or not cls._scheduler.running:
            return

        cls._scheduler.shutdown(wait=True)
        logger.info("✅ Backup-Scheduler gestoppt")

    @classmethod
    def trigger_backup_now(cls, include_pdfs: bool = True) -> dict:
        """
        Triggere Backup sofort (nicht periodisch).

        Useful für manuelle Backups über API.

        Args:
            include_pdfs: PDFs zusätzlich sichern (default: True)

        Returns:
            Status-Dict mit Backup-Informationen
        """
        return cls._perform_backup(source="manual", include_pdfs=include_pdfs)

    @classmethod
    def get_status(cls) -> dict:
        """
        Hole Status des Schedulers.

        Returns:
            Dict mit Scheduler-Status und letztem Backup-Info
        """
        scheduler_running = cls._scheduler is not None and cls._scheduler.running

        backup_status = None
        if cls._handler is not None:
            backup_status = cls._handler.get_backup_status()

        return {
            "scheduler_running": scheduler_running,
            "backup_status": backup_status,
        }

    @classmethod
    def list_jobs(cls) -> list[dict]:
        """Liste alle registrierten Scheduler-Jobs auf."""
        if cls._scheduler is None:
            return []

        jobs = []
        for job in cls._scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                }
            )

        return jobs

    @classmethod
    def list_backups(cls) -> Optional[list[dict]]:
        """
        Liste alle verfügbaren Backups auf.

        Returns:
            Liste von Backup-Objekten oder None bei Fehler
        """
        if cls._handler is None:
            logger.error("❌ BackupHandler nicht verfügbar")
            return None

        return cls._handler.list_backups()

    @classmethod
    def backup_on_shutdown(cls) -> dict:
        """Führe ein letztes Backup beim Shutdown aus (DB + PDFs)."""
        return cls._perform_backup(source="shutdown", include_pdfs=True)

    @classmethod
    def _perform_backup(cls, source: str, include_pdfs: bool = True) -> dict:
        """
        Interner Helper für alle Backup-Trigger.

        Führt DB- und PDF-Backups unabhängig voneinander aus.
        Bei Shutdown-Safety: PDF-Backup läuft auch wenn DB-Backup fehlschlägt.

        Args:
            source: Technische Bezeichnung des Triggers (z.B. "manual", "scheduled", "shutdown").
            include_pdfs: Ob zusätzlich zum DB-Backup auch ein PDF-Backup ausgeführt werden soll.

        Returns:
            dict: Ergebnisobjekt mit folgender Struktur:
                - success (bool): Gesamterfolg des Backups.
                  - Wenn ``include_pdfs`` False ist: entspricht dem DB-Backup-Erfolg.
                  - Wenn ``include_pdfs`` True ist: True, wenn entweder DB- oder PDF-Backup
                    (oder beide) erfolgreich waren.
                - timestamp (str): ISO-8601-Zeitstempel des Backup-Versuchs.
                - db_backup (dict): Informationen zum Datenbank-Backup:
                    - success (bool): Ob das DB-Backup erfolgreich war.
                    - path (str | None): Pfad zur erzeugten Backup-Datei oder None bei Fehler.
                - pdf_backup (dict, optional): Nur vorhanden, wenn ``include_pdfs`` True ist:
                    - success (bool): Ob das PDF-Backup erfolgreich war.
                    - stats: Vom ``BackupHandler.backup_pdfs`` zurückgegebene Statistik
                      (z.B. Anzahl kopierter Dateien) oder None bei Fehler.
        """
        if cls._handler is None:
            logger.error("❌ BackupHandler nicht verfügbar")
            return {"success": False, "error": "BackupHandler nicht verfügbar"}

        try:
            logger.debug(f"🔍 Starte {source}-Backup (include_pdfs={include_pdfs})")

            # Run DB backup
            backup_path = cls._handler.backup_database()
            db_success = backup_path is not None

            # Run PDF backup independently (even if DB backup failed)
            pdf_stats = None
            pdf_success = True
            if include_pdfs:
                try:
                    pdf_stats = cls._handler.backup_pdfs()
                    pdf_success = pdf_stats is not None
                except Exception as pdf_error:
                    logger.error(f"❌ PDF-Backup fehlgeschlagen: {pdf_error}")
                    pdf_success = False

            # Determine overall success and build result
            # For shutdown safety: partial success is acceptable (at least one backup succeeded)
            # - If include_pdfs=False: success = db_success
            # - If include_pdfs=True: success = db_success OR pdf_success
            if include_pdfs:
                overall_success = db_success or pdf_success
            else:
                overall_success = db_success

            result = {
                "success": overall_success,
                "timestamp": datetime.now().isoformat(),
                "db_backup": {
                    "success": db_success,
                    "path": str(backup_path) if backup_path else None,
                },
            }

            if include_pdfs:
                result["pdf_backup"] = {
                    "success": pdf_success,
                    "stats": pdf_stats,
                }

            # Log appropriate message
            if db_success and (not include_pdfs or pdf_success):
                logger.info(f"✅ {source.capitalize()}-Backup erfolgreich")
            elif db_success and not pdf_success:
                logger.warning(
                    f"⚠️ {source.capitalize()}-Backup teilweise erfolgreich: "
                    f"DB OK, PDFs fehlgeschlagen"
                )
            elif not db_success and pdf_success:
                logger.warning(
                    f"⚠️ {source.capitalize()}-Backup teilweise erfolgreich: "
                    f"DB fehlgeschlagen, PDFs OK"
                )
            else:
                logger.error(f"❌ {source.capitalize()}-Backup fehlgeschlagen")

            return result

        except Exception as e:
            logger.error(f"❌ Fehler beim {source}-Backup: {e}")
            return {
                "success": False,
                "error": "Backup fehlgeschlagen (interner Fehler)",
            }

    @staticmethod
    def _run_backup() -> None:
        """
        Interne Funktion: Führe Backup aus.

        Wird vom Scheduler aufgerufen.
        """
        BackupScheduler._perform_backup(source="scheduled", include_pdfs=True)
