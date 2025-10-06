import os
from pathlib import Path

from models import Customer, InvoiceItemRead, InvoiceRead, Profile
from services.pdf_creator import create_invoice_pdf_a4


def _dummy_data(include_tax: bool = False):
    """Hilfsfunktion: Erzeugt Dummy-Daten für Testfälle"""
    customer = Customer(
        id=1, name="Max Mustermann", address="Musterstraße 1", city="12345 Musterstadt"
    )
    profile = Profile(
        id=1,
        name="Salon Sunshine",
        address="Hauptstraße 12",
        city="12345 Berlin",
        bank_data="DE12 3456 7890 1234 5678 90",
        tax_number="12/345/67890",
    )
    invoice = InvoiceRead(
        id=1,
        number="2024|001",
        date="2024-01-01",
        customer_id=1,
        profile_id=1,
        include_tax=include_tax,
        total_amount=24.00 if not include_tax else 28.56,
        invoice_items=[
            InvoiceItemRead(
                id=1,
                invoice_id=1,
                quantity=1,
                description="Haarschnitt Damen",
                price=24.00,
            )
        ],
    )
    return customer, invoice, profile


def test_create_invoice_pdf_file_created(tmp_path):
    """Prüft, ob überhaupt eine PDF-Datei erzeugt wird"""
    customer, invoice, profile = _dummy_data()
    pdf_bytes = create_invoice_pdf_a4(customer, invoice, profile)

    # Ausgabe-Datei prüfen
    output_file = Path("output_invoice.pdf")
    assert output_file.exists(), "PDF-Datei wurde nicht erstellt"
    assert output_file.stat().st_size > 0, "PDF-Datei ist leer"

    # Rückgabewert prüfen
    assert isinstance(pdf_bytes, (bytes, bytearray))
    assert len(pdf_bytes) > 1000  # mindestens 1 KB

    # Clean up
    output_file.unlink()


def test_pdf_content_changes_with_tax():
    """Prüft, dass sich die Dateigröße bei USt unterscheidet (Indikator für Textänderung)"""
    customer, invoice_no_tax, profile = _dummy_data(include_tax=False)
    _, invoice_with_tax, _ = _dummy_data(include_tax=True)

    pdf_no_tax = create_invoice_pdf_a4(customer, invoice_no_tax, profile)
    pdf_with_tax = create_invoice_pdf_a4(customer, invoice_with_tax, profile)

    # Der PDF-Inhalt muss sich unterscheiden (wegen "Gemäß §19 UStG"-Text / USt-Zeile)
    assert pdf_no_tax != pdf_with_tax


def test_pdf_bytes_are_valid_pdf_signature():
    """Prüft, dass die ersten Bytes dem PDF-Header '%PDF' entsprechen"""
    customer, invoice, profile = _dummy_data()
    pdf_bytes = create_invoice_pdf_a4(customer, invoice, profile)

    assert pdf_bytes[:4] == b"%PDF", "PDF-Header fehlt oder Datei korrupt"
