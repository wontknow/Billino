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
    def trigger_backup_now(cls) -> dict:
        """
        Triggere Backup sofort (nicht periodisch).

        Useful für manuelle Backups über API.

        Returns:
            Status-Dict mit Backup-Informationen
        """
        if cls._handler is None:
            logger.error("❌ BackupHandler nicht verfügbar")
            return {"success": False, "error": "BackupHandler nicht verfügbar"}

        try:
            backup_path = cls._handler.backup_database()
            if backup_path:
                return {
                    "success": True,
                    "backup_path": str(backup_path),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {"success": False, "error": "Backup fehlgeschlagen"}
        except Exception as e:
            # Log the detailed exception server-side, but do not expose it to the client.
            logger.error(f"❌ Fehler beim manuellen Backup: {e}")
            return {
                "success": False,
                "error": "Backup fehlgeschlagen (interner Fehler)",
            }

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

    @staticmethod
    def _run_backup() -> None:
        """
        Interne Funktion: Führe Backup aus.

        Wird vom Scheduler aufgerufen.
        """
        if BackupScheduler._handler is None:
            logger.error("❌ BackupHandler nicht verfügbar für Schedule-Job")
            return

        try:
            logger.debug("🔍 Starte geplantes Datenbank-Backup")
            backup_path = BackupScheduler._handler.backup_database()

            if backup_path:
                # Optional: PDF-Backup auch machen
                BackupScheduler._handler.backup_pdfs()
                logger.info(f"✅ Geplantes Backup erfolgreich: {backup_path}")
            else:
                logger.error("❌ Backup fehlgeschlagen")
        except Exception as e:
            logger.error(f"❌ Fehler im Backup-Job: {e}")
