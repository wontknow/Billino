# PDF Services - Test Generation

Diese Datei ermöglicht es, verschiedene PDF-Typen mit Mock-Daten zu testen und zu visualisieren.

## Verwendung

```bash
# Aus dem backend-Verzeichnis ausführen
cd backend
python services/test_pdf_generation.py
```

## Generierte PDF-Dateien

Das Script erstellt folgende Test-PDFs:

### 1. `test_einzelrechnung.pdf`
- **Standard-Einzelrechnung** mit Mehrwertsteuer
- Enthält 2 Rechnungsposten
- Vollständige Adressdaten, Bankverbindung und Steuernummer
- Demonstriert normalen Geschäftsfall mit 19% MwSt.

### 2. `test_sammelrechnung.pdf`
- **Sammelrechnung** für mehrere Einzelrechnungen
- Aggregiert 2 Rechnungen (25 | 001 - 25 | 002)
- Zeigt Gesamtbeträge und enthaltene Rechnungsnummern
- Ideal für Hotels, Restaurants oder regelmäßige Kunden

### 3. `test_rechnung_ohne_steuer.pdf`
- **Steuerfreie Rechnung** nach §19 UStG (Kleinunternehmerregelung)
- Ohne Mehrwertsteuerausweis
- Zeigt korrekten Hinweis auf Steuerbefreiung
- Für Kleinunternehmer unter der Steuergrenze

### 4. `test_minimale_rechnung.pdf`
- **Minimal-Version** ohne optionale Felder
- Keine Bankdaten oder Steuernummer
- Nur Pflichtangaben
- Für einfache Geschäftsfälle

## Features der PDF-Generierung

✅ **Deutsche Formatierung**
- Datumsformat: DD.MM.YYYY
- Währung: EUR mit 2 Nachkommastellen
- Deutsche Beschriftungen

✅ **Steuerbehandlung**
- Automatische Netto/Brutto-Berechnung
- §19 UStG-konforme Behandlung
- Flexible Steuersätze

✅ **Professionelles Layout**
- ReportLab-basierte PDF-Generierung
- Strukturierte Tabellen für Rechnungsposten
- Responsive Adressformatierung

✅ **Robuste Datenbehandlung**
- Optionale Felder (Bankdaten, Steuernummer)
- Flexible Adressformatierung
- Sichere Datumskonvertierung

## Datei-Management

- **Test-Script**: `test_pdf_generation.py`
- **PDF-Ausgaben**: `*.pdf` (in .gitignore)
- **Automatische Bereinigung**: Bei jedem Lauf werden PDFs überschrieben

## Integration

Die generierten PDFs können verwendet werden um:
- PDF-Layout zu überprüfen
- Druckqualität zu testen
- Kundenpräsentationen vorzubereiten
- Entwicklung und Debugging zu unterstützen

---

*Diese PDFs werden nicht versioniert und dienen nur zu Testzwecken.*