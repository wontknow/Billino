"""
API-Routen für Backup-Management.

Endpoints:
- POST /backups/trigger - Manuelles Backup erzeugen
- GET /backups/status - Status der letzten Backups
- GET /backups/list - Verfügbare Backups auflisten
- GET /backups/jobs - Scheduler-Jobs auflisten
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from services.backup_scheduler import BackupScheduler
from utils.logger import logger

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("/trigger", status_code=200)
def trigger_backup():
    """
    Triggere ein manuelles Datenbank-Backup.

    **Response:**
    - success (boolean): Backup erfolgreich erstellt
    - backup_path (string): Pfad zur Backup-Datei (falls erfolgreich)
    - timestamp (string): ISO-Zeitstempel
    - error (string): Fehlermeldung (falls erfolgreich=false)

    **Beispiel-Response (Erfolg):**
    ```json
    {
        "success": true,
        "backup_path": "./backups/daily/billino_2025-12-27.db",
        "timestamp": "2025-12-27T14:30:45.123456"
    }
    ```
    """
    logger.debug("GET /backups/trigger - Manuelles Backup angefordert")

    result = BackupScheduler.trigger_backup_now()

    if result.get("success"):
        logger.info(f"Manuelles Backup erstellt: {result.get('backup_path')}")
    else:
        # Log the detailed error server-side, but return a generic message to the client.
        logger.error(f"Manuelles Backup fehlgeschlagen: {result.get('error')}")
        raise HTTPException(
            status_code=500,
            detail="Backup fehlgeschlagen. Bitte versuchen Sie es später erneut.",
        )

    return result


@router.get("/status", status_code=200)
def get_backup_status():
    """
    Hole Status der Backups und des Schedulers.

    **Response:**
    - scheduler_running (boolean): Scheduler aktiv
    - backup_status (object):
        - last_db_backup (number): Unix-Timestamp des letzten Backups
        - backup_count (number): Anzahl verfügbarer Backups
        - tauri_enabled (boolean): Tauri-Modus aktiviert
        - backup_path (string): Pfad zum Backup-Verzeichnis
        - retention_days (number): Tage bis Backup-Löschung

    **Beispiel-Response:**
    ```json
    {
        "scheduler_running": true,
        "backup_status": {
            "last_db_backup": 1735314645.123,
            "backup_count": 7,
            "tauri_enabled": false,
            "backup_path": "./backups/daily",
            "retention_days": 30
        }
    }
    ```
    """
    logger.debug("GET /backups/status - Status angefordert")

    status = BackupScheduler.get_status()

    # Konvertiere Unix-Timestamp zu ISO-Format für Response
    if status.get("backup_status") and status["backup_status"].get("last_db_backup"):
        timestamp = status["backup_status"]["last_db_backup"]
        status["backup_status"]["last_db_backup_iso"] = datetime.fromtimestamp(
            timestamp
        ).isoformat()

    logger.debug(f"Status zurückgegeben: Scheduler={status.get('scheduler_running')}")
    return status


@router.get("/list", status_code=200)
def list_backups():
    """
    Liste alle verfügbaren Backup-Dateien auf.

    **Response:**
    Array von Backup-Objekten:
    - filename (string): Dateinname (z.B. billino_2025-12-27.db)
    - path (string): Vollständiger Pfad
    - size_bytes (number): Dateigröße in Bytes
    - created_iso (string): ISO-Zeitstempel der Erstellung

    **Beispiel-Response:**
    ```json
    [
        {
            "filename": "billino_2025-12-27.db",
            "path": "./backups/daily/billino_2025-12-27.db",
            "size_bytes": 65536,
            "created_iso": "2025-12-27T02:00:00.000000"
        },
        {
            "filename": "billino_2025-12-26.db",
            "path": "./backups/daily/billino_2025-12-26.db",
            "size_bytes": 65500,
            "created_iso": "2025-12-26T02:00:00.000000"
        }
    ]
    ```
    """
    logger.debug("GET /backups/list - Backup-Liste angefordert")

    status = BackupScheduler.get_status()
    if not status.get("backup_status"):
        logger.error("Backup-Handler nicht verfügbar")
        raise HTTPException(status_code=500, detail="Backup-System nicht verfügbar")

    backup_count = status["backup_status"].get("backup_count", 0)
    backup_path = status["backup_status"].get("backup_path", "N/A")

    logger.info(f"{backup_count} Backups gefunden in {backup_path}")

    return {
        "backup_count": backup_count,
        "backup_path": backup_path,
        "retention_days": status["backup_status"].get("retention_days", 30),
    }


@router.get("/jobs", status_code=200)
def list_scheduler_jobs():
    """
    Liste alle registrierten Scheduler-Jobs auf.

    **Response:**
    Array von Job-Objekten:
    - id (string): Eindeutige Job-ID
    - name (string): Beschreibender Name

    **Beispiel-Response:**
    ```json
    {
        "jobs": [
            {
                "id": "backup_database_daily",
                "name": "Tägliches Datenbank-Backup"
            }
        ],
        "job_count": 1
    }
    ```
    """
    logger.debug("GET /backups/jobs - Jobs-Liste angefordert")

    jobs = BackupScheduler.list_jobs()
    logger.info(f"Scheduler-Jobs aufgelistet: {len(jobs)}")

    return {"jobs": jobs, "job_count": len(jobs)}
