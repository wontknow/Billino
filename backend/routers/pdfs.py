import base64
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from database import get_session
from models.invoice import Invoice
from models.stored_pdf import StoredPDF, StoredPDFCreate, StoredPDFRead
from models.summary_invoice import SummaryInvoice
from services.pdf_data_service import PDFDataService
from services.pdf_generator import PDFGenerator

router = APIRouter(prefix="/pdfs", tags=["PDFs"])


@router.post(
    "/invoices/{invoice_id}",
    response_model=StoredPDFRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_pdf(invoice_id: int, session: Session = Depends(get_session)):
    """Create and store PDF for an invoice"""
    # Check if invoice exists
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # Check if PDF already exists
    existing_pdf = session.exec(
        select(StoredPDF).where(StoredPDF.invoice_id == invoice_id)
    ).first()
    if existing_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF for this invoice already exists",
        )

    # Generate PDF
    pdf_data_service = PDFDataService(session)
    pdf_generator = PDFGenerator()

    try:
        pdf_data = pdf_data_service.get_invoice_pdf_data(invoice_id)
        pdf_bytes = pdf_generator.generate_invoice_pdf(pdf_data)

        # Encode as base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Store in database
        stored_pdf = StoredPDF(
            type="invoice", content=pdf_base64, invoice_id=invoice_id
        )
        session.add(stored_pdf)
        session.commit()
        session.refresh(stored_pdf)

        return stored_pdf

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/summary-invoices/{summary_invoice_id}",
    response_model=StoredPDFRead,
    status_code=status.HTTP_201_CREATED,
)
def create_summary_invoice_pdf(
    summary_invoice_id: int,
    customer_data: dict,  # {"customer_id": int}
    session: Session = Depends(get_session),
):
    """Create and store PDF for a summary invoice"""
    # Check if summary invoice exists
    summary_invoice = session.get(SummaryInvoice, summary_invoice_id)
    if not summary_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Summary invoice not found"
        )

    customer_id = customer_data.get("customer_id")
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="customer_id is required"
        )
    # Check if PDF already exists
    existing_pdf = session.exec(
        select(StoredPDF).where(StoredPDF.summary_invoice_id == summary_invoice_id)
    ).first()
    if existing_pdf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF for this summary invoice already exists",
        )

    # Generate PDF
    pdf_data_service = PDFDataService(session)
    pdf_generator = PDFGenerator()

    try:
        pdf_data = pdf_data_service.get_summary_invoice_pdf_data(
            summary_invoice_id, customer_id
        )
        pdf_bytes = pdf_generator.generate_summary_invoice_pdf(pdf_data)

        # Encode as base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Store in database
        stored_pdf = StoredPDF(
            type="summary_invoice",
            content=pdf_base64,
            summary_invoice_id=summary_invoice_id,
        )
        session.add(stored_pdf)
        session.commit()
        session.refresh(stored_pdf)

        return stored_pdf

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[StoredPDFRead])
def get_all_pdfs(session: Session = Depends(get_session)):
    """Get list of all stored PDFs"""
    statement = select(StoredPDF)
    pdfs = session.exec(statement).all()
    return pdfs


@router.get("/{pdf_id}", response_model=StoredPDFRead)
def get_pdf_by_id(pdf_id: int, session: Session = Depends(get_session)):
    """Get a specific PDF by ID"""
    pdf = session.get(StoredPDF, pdf_id)
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )
    return pdf


@router.delete("/{pdf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pdf(pdf_id: int, session: Session = Depends(get_session)):
    """Delete a PDF by ID"""
    pdf = session.get(StoredPDF, pdf_id)
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )

    session.delete(pdf)
    session.commit()
    return
