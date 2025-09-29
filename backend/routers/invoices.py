from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import (
    Invoice,
    InvoiceCreate,
    InvoiceItem,
    InvoiceRead,
    InvoiceItemRead,
    Profile,
    Customer,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=InvoiceRead, status_code=201)
def create_invoice(invoice: InvoiceCreate, session: Session = Depends(get_session)):
    # Muss mindestens ein Item enthalten
    if not invoice.invoice_items:
        raise HTTPException(status_code=400, detail="Invoice must have at least one item.")

    # Profile und Customer validieren
    if not session.get(Profile, invoice.profile_id):
        raise HTTPException(status_code=400, detail="Profile does not exist.")
    if not session.get(Customer, invoice.customer_id):
        raise HTTPException(status_code=400, detail="Customer does not exist.")

    # Invoice + Items in einer Transaktion anlegen
    db_invoice = Invoice(
        number=invoice.number,
        date=invoice.date,
        customer_id=invoice.customer_id,
        profile_id=invoice.profile_id,
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
