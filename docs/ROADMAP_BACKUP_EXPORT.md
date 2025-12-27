# Roadmap: Backup-Strategie & Export-Funktionalität

## Overview
Zwei aufeinander folgende Tickets zur Verbesserung der Datenverwaltung:
1. **Ticket 1: Backup-Strategie** (Datensicherung & Redundanz)
2. **Ticket 2: Export-Funktionalität** (Datenexporte für Buchhaltung & Reporting)

---

## Ticket 1: Backup-Strategie für FE/BE Trennung ✅

### Ziel
Implementierung einer Basic Backup-Strategie mit Tauri-Vorbereitung.

### Architektur
```
Backend-Dateistruktur:
backend/
├── data/
│   ├── billino.db
│   └── pdfs/
│       ├── invoices/
│       └── summary_invoices/
├── backups/ (neu)
│   └── daily/
│       └── billino_YYYY-MM-DD.db
└── main.py
```

### Implementierungs-Tasks

#### Task 1.1: Backup Handler (Core Service)
- **Datei**: `backend/services/backup_service.py`
- **Funktionen**:
  - `BackupHandler.backup_database()` - Erstellt DB-Backup
  - `BackupHandler.backup_pdfs()` - Optional: PDF-Redundanz
  - `BackupHandler.is_tauri_enabled()` - Erkennt Tauri-Umgebung
  - `BackupHandler.get_backup_path()` - Dynamische Path-Bestimmung
- **Abhängigkeiten**: 
  - `pathlib.Path`, `shutil`, `datetime`
  - Umgebungsvariable: `TAURI_ENABLED` (oder Tauri-Detection)

#### Task 1.2: Periodischer Backup-Job
- **Datei**: `backend/services/backup_scheduler.py` 
- **Funktionen**:
  - `start_backup_scheduler()` - APScheduler Job registrieren
  - Tägliches Backup um 02:00 Uhr UTC
  - Retention Policy (z.B. letzte 30 Tage bewahren)
  - Error Handling & Logging
- **In `main.py` integrieren**: Scheduler beim Startup starten
- **Abhängigkeiten**: `apscheduler`

#### Task 1.3: Backup API Endpoints (minimal)
- **Datei**: `backend/routers/backups.py` (neu)
- **Endpoints**:
  - `POST /backups/trigger` - Manuelles Backup erzeugen (Admin-only später)
  - `GET /backups/status` - Status der letzten Backups
  - `GET /backups/list` - Verfügbare Backups auflisten
- **Validierung**: Basic Checks für Dateisystem
- **Response-Format**: JSON mit Pfad, Größe, Timestamp

#### Task 1.4: Konfiguration & Environment
- **`.env` Variablen**:
  ```
  BACKUP_ENABLED=true
  BACKUP_SCHEDULE_HOUR=2
  BACKUP_RETENTION_DAYS=30
  BACKUP_PATH=./backups
  TAURI_ENABLED=false
  ```
- **`config.py` (optional)**: Zentrale Konfiguration laden

#### Task 1.5: Tests
- **`backend/tests/test_backup_service.py`**:
  - Test: Backup wird erstellt
  - Test: Backup-Datei ist lesbar
  - Test: Alte Backups werden gelöscht (Retention)
  - Test: Tauri-Detection funktioniert
- **`backend/tests/test_backup_scheduler.py`**:
  - Test: Scheduler wird gestartet
  - Test: Job läuft regelmäßig

#### Task 1.6: Logging & Monitoring
- Logger-Integration: `utils/logger.py`
- Backup-Events loggen:
  - ✅ Backup erfolgreich
  - ❌ Backup fehlgeschlagen
  - 🗂️ Alte Backups gelöscht
  - ⚠️ Disk-Space Warnungen

### Acceptance Criteria
- [ ] `BackupHandler` erstellt tägliche DB-Backups im `backups/daily/` Ordner
- [ ] Backup-Dateien sind benannt: `billino_YYYY-MM-DD.db`
- [ ] Tauri-Detektion funktioniert (für zukünftiges Ticket)
- [ ] Retention Policy: Alte Backups werden nach 30 Tagen gelöscht
- [ ] Manuelles Trigger über Endpoint möglich
- [ ] Alle Tests grün (Unit + Integration)
- [ ] Logging mit Emoji-Präfixen

### Definition of Done
- [ ] Code reviewed
- [ ] Tests mit 85%+ Coverage
- [ ] `.env.example` aktualisiert
- [ ] README/Dokumentation aktualisiert
- [ ] Commit/PR mit Conventional Commits Format

---

## Ticket 2: Export-Funktionalität (CSV/XLSX) 📋

### Ziel
Strukturierte Datenexporte für Buchhaltung, Reporting & externe Analysen.

### Exportierbare Entitäten
1. **Customers**: Name, Adresse, Stadt, Notizen, erstellt/geändert
2. **Profiles**: Firmenname, USt-Status, Bankinfos, Adresse
3. **Invoices**: Nummer, Datum, Kunde, Beträge, Steuer, Status
4. **Summary Invoices**: Nummer, Zeitraum, Gesamtbeträge, verknüpfte Rechnungen

### Implementierungs-Tasks

#### Task 2.1: Export Service (Backend Core)
- **Datei**: `backend/services/export_service.py` (neu)
- **Klassen**:
  - `BaseExporter(ABC)` - Abstract Base Class
  - `CSVExporter(BaseExporter)`
  - `XLSXExporter(BaseExporter)`
- **Funktionen** pro Exporter:
  - `export()` - Generator für Streaming
  - `format_headers()` - Spalten-Mapping
  - `format_row()` - Datensatz-Formatierung
  - `to_bytes()` - In-Memory Export
- **Abhängigkeiten**: `csv`, `openpyxl`, `io`

#### Task 2.2: Entity-spezifische Exporter
- **Datei**: `backend/services/entity_exporters.py` (neu)
- **Klassen**:
  - `CustomerExporter` - CSV/XLSX für Customers
  - `ProfileExporter` - CSV/XLSX für Profiles
  - `InvoiceExporter` - CSV/XLSX für Invoices
  - `SummaryInvoiceExporter` - CSV/XLSX für Summary Invoices
- **Features**:
  - Spalten-Mapping pro Entität
  - Datum/Zahl-Formatierung (DE-Locale)
  - Filter/Sortierung berücksichtigen
  - Chunking für große Datenmengen

#### Task 2.3: Export API Routes
- **Datei**: `backend/routers/exports.py` (neu)
- **Endpoints**:
  - `GET /exports/{entity}?format=csv|xlsx&filters=...&sort=...` → StreamingResponse
  - Validierung: entity ∈ {customers, profiles, invoices, summary_invoices}
  - Validierung: format ∈ {csv, xlsx}
  - Query-Parameter-Parsing für Filter/Sortierung
  - Content-Disposition Header: `attachment; filename="Customers_2025-12-27.csv"`

#### Task 2.4: Filter & Sortierung Integration
- **Service-Funktion**: `get_filtered_data(entity, filters, sort)`
  - Reuse der bestehenden Filter-Logik (falls vorhanden)
  - Pagination optional (Export: alle Ergebnisse)
  - Validierung gegen SQLInjection

#### Task 2.5: Frontend: Export UI
- **Komponente**: `features/exports/ExportButton.tsx` (neu)
  - Dropdown/Modal für Entität + Format
  - Hinweis zur Datenmenge ("1000+ Einträge")
  - Loading-State während Download
  - Error Handling & User-Feedback
- **Integration**: In Tabellen-Header/Toolbar (Customers, Profiles, Invoices, Summary Invoices)

#### Task 2.6: Frontend: Export Service
- **Datei**: `src/services/exports.ts` (neu)
- **Funktionen**:
  - `downloadExport(entity, format, filters, sort)` → Blob herunterladen
  - Filter-State aus Table-Context auslesen
  - Error Handling & Toast-Notifications

#### Task 2.7: CSV-Format Handling
- **Anforderungen**:
  - UTF-8 mit BOM (für Excel Kompatibilität)
  - Delimiter: `,`
  - Quoting/Escaping für Sonderzeichen
  - Header-Zeile obligatorisch
  - Datum-Format: `DD.MM.YYYY` (deutsch)
  - Dezimal-Separator: `,` (deutsch)
- **Test**: Import in Excel/Google Sheets

#### Task 2.8: XLSX-Format Handling
- **Anforderungen**:
  - Ein Arbeitsblatt pro Export
  - Auto-fit Spaltenbreiten
  - Korrekte Typen: Datum (YYYY-MM-DD), Zahl, Text
  - Header: Bold, färbig Hintergrund
  - Borders für Lesbarkeit
- **Test**: Import in Excel/Google Sheets

#### Task 2.9: Performance & Limits
- **Streaming**: Generator-basiert, keine In-Memory Komplett-Datei
- **Chunk-Size**: 1000 Rows pro Chunk (tunbar)
- **Timeout**: 5 min max pro Export
- **Rate-Limits**: Optional (z.B. 5 Exports/Minute pro User)
- **Max-Rows**: Optional (z.B. 100.000 Rows max)

#### Task 2.10: Error Handling
- Leere Ergebnisse: HTTP 200 mit leerer Datei + Header-Zeile
- Ungültige Filter: HTTP 400 mit Fehlermeldung
- Ungültige Entität/Format: HTTP 400
- Timeout: HTTP 408
- Server-Error: HTTP 500

#### Task 2.11: Tests (Backend)
- **`test_export_service.py`**:
  - CSV: Formatierung, BOM, Escaping
  - XLSX: Formatierung, Typen, Spaltenbreiten
  - Filter-Reuse: Filter werden angewendet
  - Große Datenmengen: Streaming funktioniert
  - Sonderzeichen: Umlaute, Quotes, Newlines
- **`test_export_routes.py`**:
  - Valid requests: 200 + korrekter Content-Type
  - Invalid entity: 400
  - Invalid format: 400
  - Content-Disposition Header korrekt

#### Task 2.12: Tests (Frontend)
- **`ExportButton.test.tsx`**:
  - Button rendert sich
  - Dropdown-Optionen sichtbar
  - Format-Wahl funktioniert
  - Loading-State sichtbar
  - Error-Toast bei Fehler
- **`exports.test.ts`**:
  - Download wird triggert
  - Filter werden mitgesendet
  - Blob wird korrekt gespeichert

#### Task 2.13: Dokumentation
- **Backend-README**: Export API dokumentieren (OpenAPI Auto-Docs)
- **Nutzer-Doku**: Export-Anleitung mit Screenshots
- **Troubleshooting**: Excel-Import-Probleme, Encoding-Issues

### Acceptance Criteria
- [ ] Export für alle 4 Entitäten verfügbar
- [ ] CSV: UTF-8 mit BOM, korrektes Quoting, Header vorhanden
- [ ] XLSX: Auto-fit Spaltenbreiten, korrekte Typen
- [ ] Filter/Sortierung werden berücksichtigt
- [ ] Content-Disposition Header mit korrektem Dateinamen
- [ ] Leere Ergebnisse: sinnvolle Fehlermeldung
- [ ] UI-Flow: Export-Button → Format-Wahl → Download
- [ ] Alle Tests grün (85%+ Coverage)
- [ ] Dokumentation aktualisiert

### Definition of Done
- [ ] Code reviewed
- [ ] Tests mit 85%+ Coverage
- [ ] `.env.example` aktualisiert
- [ ] Nutzer-Dokumentation verfügbar
- [ ] Frontend + Backend Tests grün
- [ ] Commit/PR mit Conventional Commits Format

---

## Zeitliche Planung

| Ticket | Phase | Geschätzter Aufwand | Status |
|--------|-------|------------------|--------|
| 1 | Entwicklung | 4-6h | 🚀 In Vorbereitung |
| 1 | Testing | 2-3h | 🚀 In Vorbereitung |
| 1 | Review/Merge | 1-2h | 🚀 In Vorbereitung |
| **1 Total** | | **7-11h** | |
| 2 | Backend | 6-8h | ⏳ Warten auf Ticket 1 |
| 2 | Frontend | 4-6h | ⏳ Warten auf Ticket 1 |
| 2 | Testing | 3-4h | ⏳ Warten auf Ticket 1 |
| 2 | Dokumentation | 2-3h | ⏳ Warten auf Ticket 1 |
| **2 Total** | | **15-21h** | |
| **Gesamt** | | **22-32h** | |

---

## Branch-Strategie

```bash
# Ticket 1: Backup-Strategie
feature/backup-strategy
└── origin/develop

# Ticket 2: Export-Funktionalität (später)
feature/export-csv-xlsx
└── feature/backup-strategy (nach Merge von Ticket 1)
```

---

## Dependencies & Libraries

### Neu erforderlich
- **Backend**:
  - `apscheduler` - Periodische Jobs
  - `openpyxl` - XLSX-Generierung
  - (csv ist stdlib)
- **Frontend**: 
  - (bestehende Dependencies reichen aus)

### Installation
```bash
# Backend
cd backend
pip install apscheduler openpyxl

# Update requirements.txt
pip freeze > requirements.txt
```

---

## Risiken & Mitigationen

| Risiko | Mitigation |
|--------|-----------|
| Disk-Space läuft voll | Retention Policy (30 Tage), Monitoring |
| Backup-Job schlägt fehl | Error Handling, Logging, Alerts |
| Export zu langsam | Streaming, Chunking, Timeouts |
| Locale-Issues (CSV/XLSX) | Unit Tests mit Sonderzeichen, manuelle Checks |
| Large Datasets (>100k Rows) | Streaming, Chunk-basiert, Rate-Limits |

---

## Out-of-Scope
- ❌ Komplexe Aggregations-Reports (Pivot/Charts)
- ❌ Cloud-Export (S3, Drive)
- ❌ Tauri-spezifische Backups (kommt in Ticket 3)
- ❌ Verschlüsselte Backups
- ❌ Automatische Cloud-Backups

---

## Next Steps

1. **Ticket 1 starten**:
   - Branch `feature/backup-strategy` erstellen
   - Task 1.1-1.6 implementieren
   - Tests grün
   - PR erstellen & mergen

2. **Ticket 2 starten** (nach Ticket 1):
   - Branch `feature/export-csv-xlsx` erstellen
   - Task 2.1-2.13 implementieren
   - Tests grün
   - PR erstellen & mergen

3. **Ticket 3 (später)**:
   - Tauri-Backup Integration
   - Desktop-App Backup-Management

---

**Status**: 🚀 Roadmap erstellt, Ticket 1 startet jetzt!
