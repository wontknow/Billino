from dataclasses import dataclass
from datetime import date
from typing import List, Optional

# Import existing models
from models import Customer, InvoiceItemRead, InvoiceRead, Profile, SummaryInvoiceRead


@dataclass
class PDFInvoiceData:
    """
    Data structure for invoice PDF generation.
    Contains all necessary information to generate a PDF invoice.
    """

    # Invoice identification
    invoice_number: str
    date: date

    # Sender (Profile) information
    sender_name: str
    sender_address: str  # Multi-line address (address + city)

    # Customer information
    customer_name: str
    customer_address: str  # Multi-line address

    # Financial data
    total_net: float
    total_tax: float
    total_gross: float
    tax_rate: float

    # Invoice items
    items: List[dict]  # List of {"description": str, "quantity": int, "price": float}

    # Optional fields (must come last)
    sender_bank_data: Optional[str] = None  # IBAN, BIC, etc.
    sender_tax_number: Optional[str] = None


@dataclass
class PDFSummaryInvoiceData:
    """
    Data structure for summary invoice PDF generation.
    Contains all necessary information to generate a PDF summary invoice.
    """

    # Summary invoice identification
    range_text: str  # e.g., "Oktober 2025"
    date: date

    # Sender (Profile) information
    sender_name: str
    sender_address: str

    # Customer information (can be different from original invoices)
    customer_name: str
    customer_address: str

    # Aggregated financial data
    total_net: float
    total_tax: float
    total_gross: float

    # Referenced invoices
    invoice_numbers: List[str]  # List of invoice numbers included in summary
    invoice_details: List[
        dict
    ]  # List of {"number": str, "customer_name": str} for detailed display

    # Optional fields (must come last)
    sender_bank_data: Optional[str] = None
    sender_tax_number: Optional[str] = None
