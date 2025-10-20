# PDF Services - Test Generation

Diese Dateien ermöglichen es, verschiedene PDF-Typen mit Mock-Daten zu testen und zu visualisieren.

## Verfügbare Test-Scripts

### 1. `test_pdf_generation.py` - Basis-Version
```bash
# Aus dem backend-Verzeichnis ausführen
cd backend
python services/test_pdf_generation.py
```

### 2. `test_pdf_generation_models.py` - Modell-basierte Version ⭐ **EMPFOHLEN**
```bash
# Aus dem backend-Verzeichnis ausführen
cd backend
python services/test_pdf_generation_models.py
```

**Warum die Modell-Version nutzen?**
- Nutzt die vorhandenen Pydantic-Modelle (`InvoiceRead`, `Customer`, `Profile`)
- Bessere Integration mit API-Endpunkten und Datenbank
- Demonstriert korrekte Verwendung der PDF-Services
- Näher an der echten Implementierung

## Generierte PDF-Dateien

### Basis-Version (`test_pdf_generation.py`)
- `test_einzelrechnung.pdf` - Standard-Rechnung mit Steuer
- `test_sammelrechnung.pdf` - Sammelrechnung mit 2 Rechnungen  
- `test_rechnung_ohne_steuer.pdf` - §19 UStG ohne Steuer
- `test_minimale_rechnung.pdf` - Minimal-Version

### Modell-Version (`test_pdf_generation_models.py`) ⭐
- `test_einzelrechnung_models.pdf` - Standard-Rechnung mit Models
- `test_sammelrechnung_models.pdf` - Sammelrechnung mit Models
- `test_rechnung_ohne_steuer_models.pdf` - §19 UStG mit Models

## Detailbeschreibung der PDF-Typen

### 1. **Standard-Einzelrechnung**
- Enthält 2 Rechnungsposten (Haarschnitt + Haarpflege)
- Vollständige Adressdaten, Bankverbindung und Steuernummer
- Demonstriert normalen Geschäftsfall mit 19% MwSt.
- Korrekte Netto/Brutto-Berechnung

### 2. **Sammelrechnung**
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
- **Korrigierte Formatierung** für Gesamtbeträge

✅ **Robuste Datenbehandlung**
- Optionale Felder (Bankdaten, Steuernummer)
- Flexible Adressformatierung
- Sichere Datumskonvertierung
- **Model-basierte Datenaufbereitung**

## Datei-Management

- **Test-Scripts**: Beide Versionen verfügbar (in .gitignore)
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