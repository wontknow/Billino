import base64
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from database import get_session
from models.invoice import Invoice
from models.stored_pdf import StoredPDF, StoredPDFCreate, StoredPDFRead
from models.summary_invoice import SummaryInvoice
from services.pdf_a6_generator import PDFA6Generator
from services.pdf_data_service import PDFDataService
from services.pdf_generator import PDFGenerator
from utils import logger

LOG_DEV = os.getenv("ENV", "dev").lower() != "prod"

router = APIRouter(prefix="/pdfs", tags=["PDFs"])


@router.post(
    "/invoices/{invoice_id}",
    response_model=StoredPDFRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice_pdf(invoice_id: int, session: Session = Depends(get_session)):
    """
    Generate and store PDF for a single invoice.

    Creates a PDF representation of an invoice and stores it in the database.
    The PDF is returned as base64-encoded content.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice to convert to PDF

    **Returns:**
    - StoredPDFRead object with base64-encoded PDF content

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "type": "invoice",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:30:00",
        "invoice_id": 1,
        "summary_invoice_id": null
    }
    ```

    **Note:** The PDF content is base64-encoded. Decode before saving to file.
    """
    logger.debug(f"📥 POST /pdfs/invoices/{invoice_id} - Creating PDF for invoice")

    # Check if invoice exists
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        logger.warning(f"⚠️ Invoice {invoice_id} not found for PDF creation")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    # Check if PDF already exists
    existing_pdf = session.exec(
        select(StoredPDF).where(StoredPDF.invoice_id == invoice_id)
    ).first()
    if existing_pdf:
        logger.warning(
            f"⚠️ PDF for invoice {invoice_id} already exists (ID: {existing_pdf.id})"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF for this invoice already exists",
        )

    # Generate PDF
    pdf_data_service = PDFDataService(session)
    pdf_generator = PDFGenerator()

    try:
        logger.debug(f"🖨️ Generating PDF data for invoice {invoice_id}...")
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

        logger.info(
            f"✅ PDF created for invoice {invoice_id} (PDF ID: {stored_pdf.id}, size: {len(pdf_base64)} bytes)"
        )
        return stored_pdf

    except ValueError as e:
        logger.error(f"❌ PDF generation failed for invoice {invoice_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/summary-invoices/{summary_invoice_id}",
    response_model=StoredPDFRead,
    status_code=status.HTTP_201_CREATED,
)
def create_summary_invoice_pdf(
    summary_invoice_id: int,
    recipient_data: Optional[
        dict
    ] = None,  # {"recipient_name"?: str, "recipient_customer_id"?: int}
    session: Session = Depends(get_session),
):
    """
    Generate and store PDF for a summary invoice.

    Creates a PDF representation of a summary invoice (Sammelrechnung) and stores it in the database.
    Optionally accepts a recipient name to be displayed in the PDF.

    **Path Parameters:**
    - `summary_invoice_id` (integer, required): ID of the summary invoice to convert to PDF

    **Request Body (optional):**
    - `recipient_data` (object, optional): Optional recipient information
        - `recipient_name` (string, optional): Name to display as recipient in PDF

    **Returns:**
    - StoredPDFRead object with base64-encoded PDF content

    **Example Request Body (optional):**
    ```json
    {
        "recipient_name": "Tax Authority"
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 2,
        "type": "summary_invoice",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:35:00",
        "invoice_id": null,
        "summary_invoice_id": 1
    }
    ```

    **Note:** The PDF content is base64-encoded. Decode before saving to file.
    """
    # Check if summary invoice exists
    summary_invoice = session.get(SummaryInvoice, summary_invoice_id)
    if not summary_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Summary invoice not found"
        )

    # Get recipient name or use fallback
    recipient_name = None
    recipient_customer_id = None
    if recipient_data:
        recipient_name = recipient_data.get("recipient_name")
        recipient_customer_id = recipient_data.get("recipient_customer_id")
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
            summary_invoice_id,
            recipient_name=recipient_name,
            recipient_customer_id=recipient_customer_id,
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


@router.post(
    "/a6-invoices",
    response_model=StoredPDFRead,
    status_code=status.HTTP_201_CREATED,
)
def create_a6_invoices_pdf(
    invoice_ids: List[int], session: Session = Depends(get_session)
):
    """
    Generate and store PDF with multiple invoices in A6 format on A4 pages.

    Creates a multi-page PDF with multiple invoices formatted on A4 pages
    (A6 format allows ~4 invoices per page). Useful for batch printing.

    **Request Body:**
    ```json
    [1, 2, 3, 4, 5]
    ```
    Or as form data: `invoice_ids=1&invoice_ids=2&invoice_ids=3`

    **Returns:**
    - StoredPDFRead object with base64-encoded PDF content

    **Example Response (201):**
    ```json
    {
        "id": 3,
        "type": "a6_invoices",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:40:00",
        "invoice_id": null,
        "summary_invoice_id": null
    }
    ```

    **Note:** The PDF content is base64-encoded. Decode before saving to file.
    """
    if not invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one invoice ID is required",
        )

    # Check if all invoices exist
    invoices = []
    for invoice_id in invoice_ids:
        invoice = session.get(Invoice, invoice_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found",
            )
        invoices.append(invoice)

    # Generate PDF data for all invoices
    pdf_data_service = PDFDataService(session)
    pdf_a6_generator = PDFA6Generator()

    try:
        # Get PDF data for each invoice
        invoice_pdf_data_list = []
        for invoice_id in invoice_ids:
            pdf_data = pdf_data_service.get_invoice_pdf_data(invoice_id)
            invoice_pdf_data_list.append(pdf_data)

        # Generate A6 layout PDF
        pdf_bytes = pdf_a6_generator.generate_a6_invoices_pdf(invoice_pdf_data_list)

        # Encode as base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Store in database with type "a6_invoices"
        stored_pdf = StoredPDF(
            type="a6_invoices",
            content=pdf_base64,
            # Note: invoice_id and summary_invoice_id are intentionally set to None for
            # a6_invoices type PDFs, as these represent a collection of invoices rather than a single entity.
        )
        session.add(stored_pdf)
        session.commit()
        session.refresh(stored_pdf)

        return stored_pdf

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=List[StoredPDFRead])
def get_all_pdfs(session: Session = Depends(get_session)):
    """
    List all stored PDFs.

    Retrieves a list of all PDF records stored in the database.

    **Returns:**
    - List of StoredPDFRead objects

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "type": "invoice",
            "content": "JVBERi0xLjQKJeLj...",
            "created_at": "2025-12-19T10:30:00",
            "invoice_id": 1,
            "summary_invoice_id": null
        },
        {
            "id": 2,
            "type": "summary_invoice",
            "content": "JVBERi0xLjQKJeLj...",
            "created_at": "2025-12-19T10:35:00",
            "invoice_id": null,
            "summary_invoice_id": 1
        }
    ]
    ```
    """
    statement = select(StoredPDF)
    pdfs = session.exec(statement).all()
    return pdfs


@router.get("/a6", response_model=List[StoredPDFRead])
def get_a6_pdfs(session: Session = Depends(get_session)):
    """
    List all A6 batch PDFs.

    Retrieves only PDFs of type 'a6_invoices' (batch invoice PDFs).

    **Returns:**
    - List of StoredPDFRead objects with type 'a6_invoices'

    **Example Response (200):**
    ```json
    [
        {
            "id": 3,
            "type": "a6_invoices",
            "content": "JVBERi0xLjQKJeLj...",
            "created_at": "2025-12-20T10:40:00",
            "invoice_id": null,
            "summary_invoice_id": null
        }
    ]
    ```
    """
    statement = select(StoredPDF).where(StoredPDF.type == "a6_invoices")
    pdfs = session.exec(statement).all()
    return pdfs


@router.get("/by-invoice/{invoice_id}", response_model=StoredPDFRead)
def get_pdf_by_invoice_id(invoice_id: int, session: Session = Depends(get_session)):
    """
    Get PDF by invoice ID.

    Retrieves the PDF associated with a specific invoice.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice

    **Returns:**
    - StoredPDFRead object

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "type": "invoice",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:30:00",
        "invoice_id": 1,
        "summary_invoice_id": null
    }
    ```
    """
    logger.debug(f"📥 GET /pdfs/by-invoice/{invoice_id} - Fetching PDF for invoice")

    pdf = session.exec(
        select(StoredPDF).where(StoredPDF.invoice_id == invoice_id)
    ).first()

    if not pdf:
        logger.warning(f"⚠️ PDF not found for invoice {invoice_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No PDF found for invoice ID {invoice_id}",
        )

    logger.debug(f"✅ PDF found for invoice {invoice_id} (PDF ID: {pdf.id})")
    return pdf


@router.get("/by-summary/{summary_invoice_id}", response_model=StoredPDFRead)
def get_pdf_by_summary_invoice_id(
    summary_invoice_id: int, session: Session = Depends(get_session)
):
    """
    Get PDF by summary invoice ID.

    Retrieves the PDF associated with a specific summary invoice.

    **Path Parameters:**
    - `summary_invoice_id` (integer, required): ID of the summary invoice

    **Returns:**
    - StoredPDFRead object

    **Example Response (200):**
    ```json
    {
        "id": 2,
        "type": "summary_invoice",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:35:00",
        "invoice_id": null,
        "summary_invoice_id": 1
    }
    ```
    """
    logger.debug(
        f"📥 GET /pdfs/by-summary/{summary_invoice_id} - Fetching PDF for summary invoice"
    )

    pdf = session.exec(
        select(StoredPDF).where(StoredPDF.summary_invoice_id == summary_invoice_id)
    ).first()

    if not pdf:
        logger.warning(f"⚠️ PDF not found for summary invoice {summary_invoice_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No PDF found for summary invoice ID {summary_invoice_id}",
        )

    logger.debug(
        f"✅ PDF found for summary invoice {summary_invoice_id} (PDF ID: {pdf.id})"
    )
    return pdf


@router.get("/{pdf_id}", response_model=StoredPDFRead)
def get_pdf_by_id(pdf_id: int, session: Session = Depends(get_session)):
    """
    Get a single PDF by ID.

    Retrieves a specific PDF record with its base64-encoded content.

    **Path Parameters:**
    - `pdf_id` (integer, required): ID of the PDF to retrieve

    **Returns:**
    - StoredPDFRead object

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "type": "invoice",
        "content": "JVBERi0xLjQKJeLj...",
        "created_at": "2025-12-19T10:30:00",
        "invoice_id": 1,
        "summary_invoice_id": null
    }
    ```
    """
    pdf = session.get(StoredPDF, pdf_id)
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )
    return pdf


@router.delete("/{pdf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pdf(pdf_id: int, session: Session = Depends(get_session)):
    """
    Delete a PDF by ID.

    Removes a PDF record from the database. The associated invoice/summary invoice is NOT deleted.

    **Path Parameters:**
    - `pdf_id` (integer, required): ID of the PDF to delete

    **Returns:**
    - No content (HTTP 204)
    """
    pdf = session.get(StoredPDF, pdf_id)
    if not pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )

    session.delete(pdf)
    session.commit()
    return
