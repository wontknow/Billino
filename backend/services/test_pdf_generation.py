#!/usr/bin/env python3
"""
PDF Test Generation Script

Erstellt Test-PDFs mit Mock-Daten für:
1. Normale Einzelrechnung
2. Sammelrechnung mit 2 Rechnungen

Diese Datei ist in .gitignore und dient nur zum lokalen Testen der PDF-Generierung.
"""

import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_generator import PDFGenerator
from services.pdf_data_structures import PDFInvoiceData, PDFSummaryInvoiceData


def create_sample_invoice_pdf():
    """Erstellt eine Beispiel-Einzelrechnung mit Mock-Daten."""
    
    # Mock-Daten für eine Einzelrechnung
    invoice_data = PDFInvoiceData(
        invoice_number="25 | 001",
        date=date(2025, 10, 20),
        sender_name="Friseursalon Schneidekunst",
        sender_address="Hauptstraße 123\n12345 Berlin",
        customer_name="Max Mustermann",
        customer_address="Max Mustermann\nMusterstraße 456\n54321 Hamburg",
        total_net=100.00,
        total_tax=19.00,
        total_gross=119.00,
        tax_rate=0.19,
        items=[
            {
                "description": "Haarschnitt und Styling",
                "quantity": 1,
                "price": 50.00
            },
            {
                "description": "Haarpflege Premium",
                "quantity": 2,
                "price": 34.50
            }
        ],
        sender_bank_data="IBAN: DE89 3704 0044 0532 0130 00\nBIC: COBADEFFXXX\nSparkasse Berlin",
        sender_tax_number="123/456/78910"
    )
    
    # PDF generieren
    generator = PDFGenerator()
    pdf_bytes = generator.generate_invoice_pdf(invoice_data)
    
    # PDF speichern
    output_path = os.path.join(os.path.dirname(__file__), "test_einzelrechnung.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✅ Einzelrechnung erstellt: {output_path}")
    return output_path


def create_sample_summary_invoice_pdf():
    """Erstellt eine Beispiel-Sammelrechnung mit Mock-Daten."""
    
    # Mock-Daten für eine Sammelrechnung
    summary_data = PDFSummaryInvoiceData(
        range_text="25 | 001 - 25 | 002",
        date=date(2025, 10, 31),
        sender_name="Friseursalon Schneidekunst",
        sender_address="Hauptstraße 123\n12345 Berlin",
        customer_name="Wellness Hotel Zur Sonne",
        customer_address="Wellness Hotel Zur Sonne\nHotelstraße 1\n98765 München",
        total_net=350.00,
        total_tax=66.50,
        total_gross=416.50,
        invoice_numbers=["25 | 001", "25 | 002"],
        sender_bank_data="IBAN: DE89 3704 0044 0532 0130 00\nBIC: COBADEFFXXX\nSparkasse Berlin",
        sender_tax_number="123/456/78910"
    )
    
    # PDF generieren
    generator = PDFGenerator()
    pdf_bytes = generator.generate_summary_invoice_pdf(summary_data)
    
    # PDF speichern
    output_path = os.path.join(os.path.dirname(__file__), "test_sammelrechnung.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✅ Sammelrechnung erstellt: {output_path}")
    return output_path


def create_no_tax_invoice_pdf():
    """Erstellt eine Beispielrechnung ohne Steuer (§19 UStG)."""
    
    # Mock-Daten für eine steuerfreie Rechnung (§19 UStG)
    invoice_data = PDFInvoiceData(
        invoice_number="25 | 003",
        date=date(2025, 10, 20),
        sender_name="Kleinunternehmer Service GmbH",
        sender_address="Kleinstraße 42\n54321 Beispielstadt",
        customer_name="Anna Schmidt",
        customer_address="Anna Schmidt\nKundenweg 789\n67890 Testdorf",
        total_net=150.00,
        total_tax=0.00,
        total_gross=150.00,
        tax_rate=0.00,
        items=[
            {
                "description": "Beratungsleistung",
                "quantity": 3,
                "price": 50.00
            }
        ],
        sender_bank_data="IBAN: DE12 3456 7890 1234 5678 90\nBIC: GENODEF1ABC\nVolksbank Beispiel",
        sender_tax_number=None  # Keine Steuernummer bei §19 UStG
    )
    
    # PDF generieren
    generator = PDFGenerator()
    pdf_bytes = generator.generate_invoice_pdf(invoice_data)
    
    # PDF speichern
    output_path = os.path.join(os.path.dirname(__file__), "test_rechnung_ohne_steuer.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✅ Rechnung ohne Steuer (§19 UStG) erstellt: {output_path}")
    return output_path


def create_minimal_invoice_pdf():
    """Erstellt eine minimale Rechnung ohne optionale Felder."""
    
    # Mock-Daten für eine minimale Rechnung
    invoice_data = PDFInvoiceData(
        invoice_number="25 | 004",
        date=date(2025, 10, 20),
        sender_name="Einfacher Service",
        sender_address="Einfachstraße 1\n12345 Minimal",
        customer_name="Kunde ohne Adresse",
        customer_address="Kunde ohne Adresse",
        total_net=50.00,
        total_tax=9.50,
        total_gross=59.50,
        tax_rate=0.19,
        items=[
            {
                "description": "Einfache Leistung",
                "quantity": 1,
                "price": 59.50
            }
        ]
        # Keine Bank-Daten und keine Steuernummer
    )
    
    # PDF generieren
    generator = PDFGenerator()
    pdf_bytes = generator.generate_invoice_pdf(invoice_data)
    
    # PDF speichern
    output_path = os.path.join(os.path.dirname(__file__), "test_minimale_rechnung.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    
    print(f"✅ Minimale Rechnung erstellt: {output_path}")
    return output_path


def main():
    """Hauptfunktion - erstellt alle Test-PDFs."""
    
    print("🎯 PDF Test Generation gestartet...")
    print("=" * 50)
    
    try:
        # Verschiedene PDF-Typen erstellen
        create_sample_invoice_pdf()
        create_sample_summary_invoice_pdf()
        create_no_tax_invoice_pdf()
        create_minimal_invoice_pdf()
        
        print("=" * 50)
        print("🎉 Alle Test-PDFs erfolgreich erstellt!")
        print("\nErstellte Dateien:")
        print("- test_einzelrechnung.pdf (Standard-Rechnung mit Steuer)")
        print("- test_sammelrechnung.pdf (Sammelrechnung mit 2 Rechnungen)")
        print("- test_rechnung_ohne_steuer.pdf (§19 UStG - ohne Steuer)")
        print("- test_minimale_rechnung.pdf (Minimal-Version)")
        
        # Hinweis zur Verwendung
        print("\n📝 Hinweise:")
        print("- Diese Dateien sind in .gitignore und werden nicht versioniert")
        print("- Zum Testen der PDF-Services verwenden")
        print("- Bei Änderungen am PDF-Layout einfach erneut ausführen")
        
    except Exception as e:
        print(f"❌ Fehler beim Erstellen der PDFs: {e}")
        raise


if __name__ == "__main__":
    main()