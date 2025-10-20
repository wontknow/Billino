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

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/number-preview")
def get_invoice_number_preview(session: Session = Depends(get_session)):
    """
    Get a preview of what the next invoice number would be globally.
    Useful for frontend to show users what number their invoice will get.

    Note: Numbers are sequential across all profiles (German tax law compliance).
    """
    next_number = get_preview_invoice_number(session)
    return {"preview_number": next_number}


@router.post("/", response_model=InvoiceRead, status_code=201)
def create_invoice(invoice: InvoiceCreate, session: Session = Depends(get_session)):

    profile = session.get(Profile, invoice.profile_id)
    customer = session.get(Customer, invoice.customer_id)
    # Profile und Customer validieren
    if not profile:
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

    if difference >= tolerance:
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
    invoices = session.exec(select(Invoice)).all()
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
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
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
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
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
    return
