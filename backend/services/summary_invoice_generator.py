from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    Invoice,
    Profile,
    SummaryInvoice,
    SummaryInvoiceCreate,
    SummaryInvoiceLink,
    SummaryInvoiceRead,
)


def create_summary_invoice(
    session: Session, summary: SummaryInvoiceCreate
) -> SummaryInvoiceRead:
    """
    Create a summary invoice for the given profile and list of invoice IDs.
    
    If recipient_customer_id is provided, that customer will be used as the recipient.
    Otherwise, the customers from the invoices will be used.
    """
    profile_id = summary.profile_id
    invoice_ids = summary.invoice_ids
    # Fetch the profile
    profile = session.get(Profile, profile_id)
    if not profile:
        raise ValueError("Profile not found")

    # Validate recipient customer if provided
    if summary.recipient_customer_id:
        from models import Customer
        recipient_customer = session.get(Customer, summary.recipient_customer_id)
        if not recipient_customer:
            raise ValueError(f"Recipient customer with ID {summary.recipient_customer_id} not found")

    # Fetch the invoices
    invoices = []
    for invoice_id in invoice_ids:
        invoice = session.get(Invoice, invoice_id)
        if invoice and invoice.profile_id == profile_id:
            invoices.append(invoice)

    if not invoices:
        raise ValueError("No valid invoices found for the given IDs")

    # Calculate amounts: total_net, total_tax, total_gross, depending on if tax is included, tax rate and is_gross_amount
    total_net = 0.0
    total_tax = 0.0
    total_gross = 0.0

    for invoice in invoices:
        rate = invoice.tax_rate or 0.0

        # Fall 1️⃣: Kleinunternehmer / keine Steuer
        if not invoice.include_tax or rate == 0:
            net = invoice.total_amount
            tax = 0.0
            gross = invoice.total_amount

        # Fall 2️⃣: Bruttobetrag angegeben (is_gross_amount=True)
        elif invoice.is_gross_amount:
            gross = invoice.total_amount
            net = gross / (1 + rate)
            tax = gross - net

        # Fall 3️⃣: Nettobetrag angegeben (is_gross_amount=False)
        else:
            net = invoice.total_amount
            tax = net * rate
            gross = net + tax

        total_net += net
        total_tax += tax
        total_gross += gross

    # Runde alles sauber (z. B. auf 2 Nachkommastellen)
    total_net = round(total_net, 2)
    total_tax = round(total_tax, 2)
    total_gross = round(total_gross, 2)

    # Range Text ist kleinste und größte Rechnungsnummer (25 | 0025 - 25 | 0040)
    # Jahr aus Number extrahieren
    invoice_year = invoices[0].number.split(" | ")[0]
    numbers = []
    # invoice number aus string auslesen
    for inv in invoices:
        numbers.append(int(inv.number.split(" | ")[1]))
    min_number = min(numbers)
    max_number = max(numbers)
    # Rangetext zusammenbauen (z.B. 25 | 0025 - 25 | 0040)
    range = f"{invoice_year} | {str(min_number).zfill(4)} - {invoice_year} | {str(max_number).zfill(4)}"

    # Create summary invoice
    summary_invoice = SummaryInvoice(
        range_text=range,
        profile_id=profile_id,
        date=(summary.date or datetime.now(timezone.utc).isoformat()),
        total_net=total_net,
        total_tax=total_tax,
        total_gross=total_gross,
        recipient_customer_id=getattr(summary, "recipient_customer_id", None),
    )
    session.add(summary_invoice)
    session.flush()

    # Get the invoice IDs BEFORE committing (while objects are still attached)
    invoice_ids = [invoice.id for invoice in invoices]

    # Link invoices to summary invoice
    for invoice in invoices:
        link = SummaryInvoiceLink(
            summary_invoice_id=summary_invoice.id, invoice_id=invoice.id
        )
        session.add(link)

    session.commit()

    # get the summary invoice again to ensure it's up to date
    summary_invoice = session.get(SummaryInvoice, summary_invoice.id)
    if not summary_invoice:
        raise ValueError("Failed to retrieve the created summary invoice")

    # Create the response object directly from the summary_invoice object
    summary_invoice_response = SummaryInvoiceRead(
        id=summary_invoice.id,
        range_text=summary_invoice.range_text,
        date=summary_invoice.date,
        profile_id=summary_invoice.profile_id,
        total_net=summary_invoice.total_net,
        total_tax=summary_invoice.total_tax,
        total_gross=summary_invoice.total_gross,
        invoice_ids=invoice_ids,
    )

    return summary_invoice_response
