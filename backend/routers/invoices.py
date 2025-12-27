from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import (
    Customer,
    Invoice,
    InvoiceCreate,
    InvoiceItem,
    InvoiceItemRead,
    InvoiceRead,
    Profile,
    SummaryInvoiceCreate,
    SummaryInvoiceRead,
)
from services import (
    create_summary_invoice,
    generate_next_invoice_number,
    get_preview_invoice_number,
)
from services.background_pdf_generator import BackgroundPDFGenerator
from services.pdf_generation_service import generate_pdf_for_invoice
from utils import logger

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/number-preview")
def get_invoice_number_preview(session: Session = Depends(get_session)):
    """
    Get a preview of the next invoice number.

    Returns what the next automatically generated invoice number will be.
    Useful for frontend to show users what number their invoice will get.

    Note: Invoice numbers are sequential across all profiles (German tax law compliance).
    Format: "YY | NNN" (e.g., "25 | 001")

    **Returns:**
    - `preview_number` (string): The next invoice number in format "YY | NNN"

    **Example Response (200):**
    ```json
    {
        "preview_number": "25 | 042"
    }
    ```
    """
    logger.debug("🔢 GET /invoices/number-preview - Fetching next invoice number")
    next_number = get_preview_invoice_number(session)
    logger.debug(f"✅ Next invoice number preview: {next_number}")
    return {"preview_number": next_number}


@router.post("/", response_model=InvoiceRead, status_code=201)
def create_invoice(invoice: InvoiceCreate, session: Session = Depends(get_session)):
    """
    Create a new invoice.

    Creates a new invoice with automatic invoice number generation. The request must include
    at least one invoice item. The sum of invoice items must match the total_amount (within 0.01 tolerance).

    **Request Body:**
    - `date` (string, required): Invoice date (format: "YYYY-MM-DD")
    - `customer_id` (integer, required): ID of the customer
    - `profile_id` (integer, required): ID of the seller profile
    - `total_amount` (float, required): Total amount (must match sum of items)
    - `invoice_items` (array, required): At least one invoice item with:
        - `quantity` (integer): Quantity of items
        - `description` (string): Item description
        - `price` (float): Price per item
        - `tax_rate` (float, optional): Individual tax rate for this item
    - `include_tax` (boolean, optional): Whether to include VAT. If not provided, inherits from profile
    - `tax_rate` (float, optional): VAT rate as decimal (0.19 for 19%). Required if include_tax=true
    - `is_gross_amount` (boolean, optional): Whether total_amount is gross or net (default: false = net)

    **Returns:**
    - InvoiceRead object with assigned invoice number and ID

    **Example Request:**
    ```json
    {
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "invoice_items": [
            {
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00
            }
        ],
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "number": "25 | 001",
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true,
        "invoice_items": [
            {
                "id": 1,
                "invoice_id": 1,
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00,
                "tax_rate": null
            }
        ]
    }
    ```
    """
    logger.debug(
        f"📝 POST /invoices - Creating invoice for customer_id={invoice.customer_id}, profile_id={invoice.profile_id}"
    )

    profile = session.get(Profile, invoice.profile_id)
    customer = session.get(Customer, invoice.customer_id)
    # Profile und Customer validieren
    if not profile:
        logger.error(f"❌ Profile {invoice.profile_id} not found")
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "loc": ["body", "profile_id"],
                    "msg": "Profile does not exist.",
                    "type": "value_error",
                }
            ],
        )
    if not customer:
        logger.error(f"❌ Customer {invoice.customer_id} not found")
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "loc": ["body", "customer_id"],
                    "msg": "Customer does not exist.",
                    "type": "value_error",
                }
            ],
        )

    # Generate next invoice number automatically (globally, not per profile)
    invoice_number = generate_next_invoice_number(session)
    logger.debug(f"🔢 Generated invoice number: {invoice_number}")

    # Vererbe Steuersatz vom Profil, wenn nicht explizit angegeben
    if invoice.include_tax is None:
        invoice.include_tax = profile.include_tax

    if invoice.include_tax:
        if invoice.tax_rate is None:
            invoice.tax_rate = profile.default_tax_rate
    else:
        invoice.tax_rate = 0.0

    # 1. Summenprüfung vor DB-Aktion
    calculated_total = round(
        sum(item.quantity * item.price for item in invoice.invoice_items), 2
    )
    tolerance = 0.01
    difference = round(calculated_total - invoice.total_amount, 2)
    logger.debug(
        f"💰 Total validation - Calculated: {calculated_total}, Expected: {invoice.total_amount}, Diff: {difference}"
    )

    if difference >= tolerance:
        logger.error(f"❌ Total amount exceeds expected by {difference}")
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", "total_amount"],
                    "msg": "Sum of invoice items exceeds total_amount by more than 0.01.",
                    "type": "value_error",
                }
            ],
        )

    if -difference >= tolerance:
        logger.error(f"❌ Total amount is less than expected by {-difference}")
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", "total_amount"],
                    "msg": "Sum of invoice items is less than total_amount by more than 0.01.",
                    "type": "value_error",
                }
            ],
        )

    # Invoice + Items in einer Transaktion anlegen
    db_invoice = Invoice(
        number=invoice_number,  # Use generated number
        date=invoice.date,
        customer_id=invoice.customer_id,
        profile_id=invoice.profile_id,
        include_tax=invoice.include_tax,
        tax_rate=invoice.tax_rate,
        is_gross_amount=invoice.is_gross_amount,
        total_amount=invoice.total_amount,
    )
    session.add(db_invoice)
    session.flush()  # erzeugt ID für Invoice, ohne Commit

    db_items: list[InvoiceItem] = []
    for item in invoice.invoice_items:
        db_item = InvoiceItem(
            invoice_id=db_invoice.id,
            quantity=item.quantity,
            description=item.description,
            price=item.price,
        )
        session.add(db_item)
        db_items.append(db_item)

    session.commit()
    session.refresh(db_invoice)
    for db_item in db_items:
        session.refresh(db_item)

    logger.info(
        f"✅ Invoice {invoice_number} created successfully (id={db_invoice.id})"
    )

    # Trigger PDF generation asynchronously in background thread
    logger.debug(
        f"🖨️ Starting background thread for PDF generation (invoice {db_invoice.id})..."
    )
    BackgroundPDFGenerator.generate_in_background(
        pdf_generation_func=generate_pdf_for_invoice,
        entity_id=db_invoice.id,
        entity_type="invoice",
    )

    return InvoiceRead(
        id=db_invoice.id,
        number=db_invoice.number,
        date=db_invoice.date,
        customer_id=db_invoice.customer_id,
        profile_id=db_invoice.profile_id,
        include_tax=db_invoice.include_tax,
        tax_rate=db_invoice.tax_rate,
        is_gross_amount=db_invoice.is_gross_amount,
        total_amount=db_invoice.total_amount,
        invoice_items=[
            InvoiceItemRead(
                id=item.id,
                invoice_id=item.invoice_id,
                quantity=item.quantity,
                description=item.description,
                price=item.price,
            )
            for item in db_items
        ],
    )


@router.get("/", response_model=list[InvoiceRead])
def read_invoices(session: Session = Depends(get_session)):
    """
    List all invoices.

    Retrieves a list of all invoices in the database with their line items.

    **Returns:**
    - List of InvoiceRead objects with all related invoice items

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "number": "25 | 001",
            "date": "2025-12-19",
            "customer_id": 1,
            "profile_id": 1,
            "total_amount": 119.00,
            "include_tax": true,
            "tax_rate": 0.19,
            "is_gross_amount": true,
            "invoice_items": [
                {
                    "id": 1,
                    "invoice_id": 1,
                    "quantity": 2,
                    "description": "Consulting Service",
                    "price": 50.00,
                    "tax_rate": null
                }
            ]
        }
    ]
    ```
    """
    logger.debug("📄 GET /invoices - Listing all invoices")
    invoices = session.exec(select(Invoice)).all()
    logger.debug(f"✅ Found {len(invoices)} invoices")
    result = []
    for inv in invoices:
        items = session.exec(
            select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)
        ).all()
        result.append(
            InvoiceRead(
                id=inv.id,
                number=inv.number,
                date=inv.date,
                customer_id=inv.customer_id,
                profile_id=inv.profile_id,
                include_tax=inv.include_tax,
                total_amount=inv.total_amount,
                invoice_items=[
                    InvoiceItemRead(
                        id=item.id,
                        invoice_id=item.invoice_id,
                        quantity=item.quantity,
                        description=item.description,
                        price=item.price,
                    )
                    for item in items
                ],
            )
        )
    return result


@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, session: Session = Depends(get_session)):
    """
    Get a single invoice by ID.

    Retrieves detailed information about a specific invoice including all line items.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice to retrieve

    **Returns:**
    - InvoiceRead object with all related invoice items

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "number": "25 | 001",
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true,
        "invoice_items": [
            {
                "id": 1,
                "invoice_id": 1,
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00,
                "tax_rate": null
            }
        ]
    }
    ```
    """
    logger.debug(f"📖 GET /invoices/{invoice_id} - Fetching invoice")
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        logger.error(f"❌ Invoice {invoice_id} not found")
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "invoice_id"],
                    "msg": "Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    logger.debug(f"✅ Invoice {invoice_id} fetched with {len(items)} items")
    return InvoiceRead(
        id=invoice.id,
        number=invoice.number,
        date=invoice.date,
        customer_id=invoice.customer_id,
        profile_id=invoice.profile_id,
        include_tax=invoice.include_tax,
        total_amount=invoice.total_amount,
        invoice_items=[
            InvoiceItemRead(
                id=item.id,
                invoice_id=item.invoice_id,
                quantity=item.quantity,
                description=item.description,
                price=item.price,
            )
            for item in items
        ],
    )


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, session: Session = Depends(get_session)):
    """
    Delete an invoice.

    Removes an invoice and all its related line items from the database.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice to delete

    **Returns:**
    - No content (HTTP 204)

    **Note:** Deleting an invoice will also remove all associated invoice items.
    """
    logger.info(f"🗑️ DELETE /invoices/{invoice_id} - Deleting invoice")
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        logger.error(f"❌ Invoice {invoice_id} not found for deletion")
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "invoice_id"],
                    "msg": "Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    # Zuerst die zugehörigen Items löschen
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    for item in items:
        session.delete(item)
    # Dann die Invoice selbst löschen
    session.delete(invoice)
    session.commit()
    logger.info(f"✅ Invoice {invoice_id} deleted successfully with {len(items)} items")
    return
