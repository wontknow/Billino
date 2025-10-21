#!/usr/bin/env python3
"""
Demo script for A6 PDF generator.

This script demonstrates the A6 PDF generation functionality
with realistic invoice data and generates a sample PDF file.
"""

from datetime import date
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_a6_generator_simple import PDFA6GeneratorSimple
from services.pdf_data_structures import PDFInvoiceData


def create_test_invoice_data(invoice_number: str, customer_name: str, amount: float = 119.0) -> PDFInvoiceData:
    """Create realistic test invoice data with varying amounts"""
    net = amount / 1.19
    tax = amount - net
    
    return PDFInvoiceData(
        invoice_number=invoice_number,
        date=date.today(),
        sender_name="Billino Demo GmbH",
        sender_address="Musterstraße 123\n12345 Musterstadt",
        customer_name=customer_name,
        customer_address=f"{customer_name}\nKundenstraße 456\n54321 Kundenstadt",
        total_net=round(net, 2),
        total_tax=round(tax, 2),
        total_gross=round(amount, 2),
        tax_rate=0.19,
        items=[
            {
                "description": "Beratungsleistung",
                "quantity": 1,
                "price": round(net, 2)
            }
        ],
        sender_tax_number="123/456/78901",
        sender_bank_data="IBAN: DE12 3456 7890 1234 5678 90"
    )


def main():
    """Demo the A6 PDF generator with realistic invoice data"""
    print("🎯 A6 PDF Generator Demo")
    print("========================")
    
    # Create generator
    generator = PDFA6GeneratorSimple()
    
    # Create 4 demo invoices with different amounts
    invoices = [
        create_test_invoice_data("2024-001", "Müller GmbH & Co. KG", 238.00),
        create_test_invoice_data("2024-002", "Schmidt Consulting AG", 476.00), 
        create_test_invoice_data("2024-003", "Weber Software Solutions", 119.00),
        create_test_invoice_data("2024-004", "Fischer Dienstleistungen", 357.00),
    ]
    
    print(f"📄 Generating demo PDF with {len(invoices)} invoices...")
    
    try:
        pdf_bytes = generator.generate_a6_invoices_pdf(invoices)
        
        # Save demo file in scripts directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "A6_Demo_4_Invoices.pdf")
        
        with open(output_file, "wb") as f:
            f.write(pdf_bytes)
        
        print(f"✅ SUCCESS! Generated {os.path.basename(output_file)} ({len(pdf_bytes):,} bytes)")
        print()
        print("📋 Demo Features:")
        print("- 4 invoices in 2x2 grid layout")
        print("- Properly centered on A4 page")
        print("- Crop marks for cutting")
        print("- Each invoice in A6 format")
        print("- Realistic customer data")
        print()
        print(f"📁 File saved to: {output_file}")
        print(f"💡 Open the PDF to see the A6 layout in action!")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()