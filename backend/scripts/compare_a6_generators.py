#!/usr/bin/env python3
"""
Comparison script for A6 PDF generators.

This script compares the Original (Frame-based) and Simple (Canvas-based)
A6 PDF generators to verify they produce similar results.
"""

import os
import sys
from datetime import date

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_a6_generator import PDFA6Generator
from services.pdf_a6_generator_simple import PDFA6GeneratorSimple
from services.pdf_data_structures import PDFInvoiceData


def create_test_invoice_data(invoice_number: str, customer_name: str) -> PDFInvoiceData:
    """Create identical test invoice data for both generators"""
    return PDFInvoiceData(
        invoice_number=invoice_number,
        date=date.today(),
        sender_name="Billino Vergleich GmbH",
        sender_address="Vergleichsstraße 123\n12345 Vergleichsstadt",
        customer_name=customer_name,
        customer_address=f"{customer_name}\nKundenstraße 456\n54321 Kundenstadt",
        total_net=100.0,
        total_tax=19.0,
        total_gross=119.0,
        tax_rate=0.19,
        items=[{"description": "Vergleichsleistung", "quantity": 1, "price": 100.0}],
        sender_tax_number="123/456/78901",
        sender_bank_data="IBAN: DE12 3456 7890 1234 5678 90",
    )


def main():
    """Compare both A6 PDF generators"""
    print("⚖️  A6 PDF Generator Comparison")
    print("===============================")

    # Create test data
    invoices = []
    for i in range(4):
        invoice_data = create_test_invoice_data(
            f"CMP-{i+1:03d}", f"Vergleich Kunde {i+1} GmbH"
        )
        invoices.append(invoice_data)

    print(f"📄 Testing with {len(invoices)} invoices...")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Test Original Generator
    print("\n🔧 Testing ORIGINAL Generator (Frame-based)...")
    try:
        original_generator = PDFA6Generator()
        original_pdf = original_generator.generate_a6_invoices_pdf(invoices)

        original_file = os.path.join(script_dir, "Comparison_Original_A6.pdf")
        with open(original_file, "wb") as f:
            f.write(original_pdf)

        print(f"✅ Original: {len(original_pdf):,} bytes")

    except Exception as e:
        print(f"❌ Original failed: {e}")
        original_pdf = None

    # Test Simple Generator
    print("\n🎨 Testing SIMPLE Generator (Canvas-based)...")
    try:
        simple_generator = PDFA6GeneratorSimple()
        simple_pdf = simple_generator.generate_a6_invoices_pdf(invoices)

        simple_file = os.path.join(script_dir, "Comparison_Simple_A6.pdf")
        with open(simple_file, "wb") as f:
            f.write(simple_pdf)

        print(f"✅ Simple: {len(simple_pdf):,} bytes")

    except Exception as e:
        print(f"❌ Simple failed: {e}")
        simple_pdf = None

    print("\n📊 Comparison Results:")
    print("=" * 40)

    if original_pdf and simple_pdf:
        size_diff = abs(len(original_pdf) - len(simple_pdf))
        percentage_diff = (size_diff / max(len(original_pdf), len(simple_pdf))) * 100

        print(f"📏 Size difference: {size_diff:,} bytes ({percentage_diff:.1f}%)")
        print(
            f"🏆 Smaller file: {'Simple' if len(simple_pdf) < len(original_pdf) else 'Original'}"
        )

    print("\nBoth generators should produce:")
    print("✓ Properly centered 2x2 layout")
    print("✓ Equal margins on all sides")
    print("✓ Accurate crop marks")
    print("✓ A6-sized invoices on A4 page")
    print()
    print("📁 Generated files in scripts/ directory:")
    print("- Comparison_Original_A6.pdf (Frame-based)")
    print("- Comparison_Simple_A6.pdf (Canvas-based)")
    print()
    print("💡 Open both PDFs to verify identical positioning!")


if __name__ == "__main__":
    main()
