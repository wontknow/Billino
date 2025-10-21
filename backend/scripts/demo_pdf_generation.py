#!/usr/bin/env python3
"""
PDF Generation Demo Script

This script demonstrates PDF generation with mock data for:
1. Individual invoices (standard format)
2. Summary invoices (multiple invoices combined)

Useful for testing PDF generation functionality and visual design.
"""

import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_data_structures import PDFInvoiceData, PDFSummaryInvoiceData
from services.pdf_generator import PDFGenerator


def create_sample_invoice_pdf():
    """Generate a sample individual invoice with mock data."""

    # Mock data for individual invoice
    invoice_data = PDFInvoiceData(
        invoice_number="DEMO-001",
        date=date.today(),
        sender_name="Friseursalon Schneidekunst",
        sender_address="Hauptstraße 123\n12345 Berlin",
        customer_name="Max Mustermann",
        customer_address="Max Mustermann\nMusterstraße 456\n54321 Hamburg",
        total_net=100.00,
        total_tax=19.00,
        total_gross=119.00,
        tax_rate=0.19,
        items=[
            {"description": "Haarschnitt und Styling", "quantity": 1, "price": 50.00},
            {"description": "Haarpflege Premium", "quantity": 2, "price": 25.00},
        ],
        sender_bank_data="IBAN: DE89 3704 0044 0532 0130 00\nBIC: COBADEFFXXX\nSparkasse Berlin",
        sender_tax_number="123/456/78910",
    )

    # Generate PDF
    generator = PDFGenerator()
    pdf_bytes = generator.generate_invoice_pdf(invoice_data)

    # Save PDF in scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "Demo_Individual_Invoice.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(
        f"✅ Individual invoice created: {os.path.basename(output_path)} ({len(pdf_bytes):,} bytes)"
    )
    return output_path


def create_sample_summary_invoice_pdf():
    """Generate a sample summary invoice with mock data."""

    # Mock data for summary invoice
    summary_data = PDFSummaryInvoiceData(
        range_text="DEMO-001 - DEMO-002",
        date=date.today(),
        sender_name="Friseursalon Schneidekunst",
        sender_address="Hauptstraße 123\n12345 Berlin",
        customer_name="Wellness Hotel Zur Sonne",
        customer_address="Wellness Hotel Zur Sonne\nHotelstraße 1\n98765 München",
        total_net=350.00,
        total_tax=66.50,
        total_gross=416.50,
        invoice_numbers=["DEMO-001", "DEMO-002"],
        sender_bank_data="IBAN: DE89 3704 0044 0532 0130 00\nBIC: COBADEFFXXX\nSparkasse Berlin",
        sender_tax_number="123/456/78910",
    )

    # Generate PDF
    generator = PDFGenerator()
    pdf_bytes = generator.generate_summary_invoice_pdf(summary_data)

    # Save PDF in scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "Demo_Summary_Invoice.pdf")
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    print(
        f"✅ Summary invoice created: {os.path.basename(output_path)} ({len(pdf_bytes):,} bytes)"
    )
    return output_path


def main():
    """Generate demo PDFs for both invoice types."""
    print("🎯 PDF Generation Demo")
    print("======================")
    print("Generating sample PDFs with professional design...")
    print()

    try:
        # Generate individual invoice
        print("📄 Creating individual invoice...")
        create_sample_invoice_pdf()

        # Generate summary invoice
        print("📊 Creating summary invoice...")
        create_sample_summary_invoice_pdf()

        print()
        print("🎉 Demo PDFs generated successfully!")
        print()
        print("📁 Generated files in scripts/ directory:")
        print("- Demo_Individual_Invoice.pdf")
        print("- Demo_Summary_Invoice.pdf")
        print()
        print("💡 These PDFs showcase the professional design with:")
        print("  ✓ Elegant color palette")
        print("  ✓ Professional typography")
        print("  ✓ Modern layout design")
        print("  ✓ Structured table formatting")

    except Exception as e:
        print(f"❌ Error generating demo PDFs: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
