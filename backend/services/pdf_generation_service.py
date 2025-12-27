"""
Service for background PDF generation.
Handles asynchronous PDF creation after invoice/summary invoice creation.
"""

import base64
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models.invoice import Invoice
from models.stored_pdf import StoredPDF
from models.summary_invoice import SummaryInvoice
from services.pdf_data_service import PDFDataService
from services.pdf_generator import PDFGenerator
from utils import logger


def generate_pdf_for_invoice(session: Session, invoice_id: int) -> bool:
    """
    Generate and store PDF for a single invoice asynchronously.

    **Args:**
    - session: Database session
    - invoice_id: ID of the invoice to generate PDF for

    **Returns:**
    - True if PDF was generated successfully, False if it already exists or invoice not found
    """
    try:
        logger.debug(f"📝 PDF Generation: Checking for invoice {invoice_id}")

        # Check if invoice exists
        invoice = session.get(Invoice, invoice_id)
        if not invoice:
            logger.error(f"❌ Invoice {invoice_id} not found for PDF generation")
            return False

        # Early check if PDF already exists (optimization to avoid expensive PDF generation)
        # Note: There is a small race window between this check and the final commit where
        # another thread could create the PDF, causing unnecessary generation work. This is
        # acceptable because:
        # 1. The unique constraint prevents duplicate PDFs (functionally correct)
        # 2. PDF generation is async background work (not user-facing)
        # 3. The race window is small in practice
        # 4. IntegrityError pattern is simpler than SELECT FOR UPDATE locking
        # Alternative: Use SELECT FOR UPDATE or advisory locks, but this adds complexity
        # and potential deadlock scenarios without significant benefit for this use case.
        existing_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == invoice_id)
        ).first()
        if existing_pdf:
            logger.debug(
                f"ℹ️ PDF for invoice {invoice_id} already exists (ID: {existing_pdf.id})"
            )
            return False

        logger.debug(f"🖨️ PDF Generation: Generating PDF for invoice {invoice_id}...")

        # Generate PDF
        pdf_data_service = PDFDataService(session)
        pdf_generator = PDFGenerator()

        pdf_data = pdf_data_service.get_invoice_pdf_data(invoice_id)
        pdf_bytes = pdf_generator.generate_invoice_pdf(pdf_data)

        # Encode as base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # Store in database
        stored_pdf = StoredPDF(
            type="invoice", content=pdf_base64, invoice_id=invoice_id
        )
        session.add(stored_pdf)

        try:
            session.commit()
            session.refresh(stored_pdf)
            logger.info(
                f"✅ PDF generated for invoice {invoice_id} (PDF ID: {stored_pdf.id}, size: {len(pdf_base64)} bytes)"
            )
            return True
        except IntegrityError as e:
            # Another thread/process created the PDF first (caught by unique constraint)
            # Check if this is a unique constraint violation on invoice_id
            session.rollback()
            error_msg = str(e).lower()
            if "unique" in error_msg or "invoice_id" in error_msg:
                logger.debug(
                    f"ℹ️ PDF for invoice {invoice_id} was created by another process"
                )
                return False
            else:
                # Re-raise if it's a different integrity error
                logger.error(
                    f"❌ Unexpected IntegrityError for invoice {invoice_id}: {str(e)}"
                )
                raise

    except Exception as e:
        session.rollback()
        logger.error(
            f"❌ Failed to generate PDF for invoice {invoice_id}: {str(e)}",
            exc_info=True,
        )
        return False


def generate_pdf_for_summary_invoice(
    session: Session,
    summary_invoice_id: int,
    recipient_name: Optional[str] = None,
    recipient_customer_id: Optional[int] = None,
) -> bool:
    """
    Generate and store PDF for a summary invoice asynchronously.

    **Args:**
    - session: Database session
    - summary_invoice_id: ID of the summary invoice to generate PDF for
    - recipient_name: Optional recipient name for the PDF

    **Returns:**
    - True if PDF was generated successfully, False if it already exists or summary invoice not found
    """
    try:
        logger.debug(
            f"📝 PDF Generation: Checking for summary invoice {summary_invoice_id}"
        )

        # Check if summary invoice exists
        summary_invoice = session.get(SummaryInvoice, summary_invoice_id)
        if not summary_invoice:
            logger.error(
                f"❌ Summary invoice {summary_invoice_id} not found for PDF generation"
            )
            return False

        # Early check if PDF already exists (optimization to avoid expensive PDF generation)
        # Note: There is a small race window between this check and the final commit where
        # another thread could create the PDF, causing unnecessary generation work. This is
        # acceptable because:
        # 1. The unique constraint prevents duplicate PDFs (functionally correct)
        # 2. PDF generation is async background work (not user-facing)
        # 3. The race window is small in practice
        # 4. IntegrityError pattern is simpler than SELECT FOR UPDATE locking
        # Alternative: Use SELECT FOR UPDATE or advisory locks, but this adds complexity
        # and potential deadlock scenarios without significant benefit for this use case.
        existing_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.summary_invoice_id == summary_invoice_id)
        ).first()
        if existing_pdf:
            logger.debug(
                f"ℹ️ PDF for summary invoice {summary_invoice_id} already exists (ID: {existing_pdf.id})"
            )
            return False

        logger.debug(
            f"🖨️ PDF Generation: Generating PDF for summary invoice {summary_invoice_id}..."
        )

        # Generate PDF
        pdf_data_service = PDFDataService(session)
        pdf_generator = PDFGenerator()

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

        try:
            session.commit()
            session.refresh(stored_pdf)
            logger.info(
                f"✅ PDF generated for summary invoice {summary_invoice_id} (PDF ID: {stored_pdf.id}, size: {len(pdf_base64)} bytes, recipient: {recipient_name or 'N/A'})"
            )
            return True
        except IntegrityError as e:
            # Another thread/process created the PDF first (caught by unique constraint)
            # Check if this is a unique constraint violation on summary_invoice_id
            session.rollback()
            error_msg = str(e).lower()
            if "unique" in error_msg or "summary_invoice_id" in error_msg:
                logger.debug(
                    f"ℹ️ PDF for summary invoice {summary_invoice_id} was created by another process"
                )
                return False
            else:
                # Re-raise if it's a different integrity error
                logger.error(
                    f"❌ Unexpected IntegrityError for summary invoice {summary_invoice_id}: {str(e)}"
                )
                raise

    except Exception as e:
        session.rollback()
        logger.error(
            f"❌ Failed to generate PDF for summary invoice {summary_invoice_id}: {str(e)}",
            exc_info=True,
        )
        return False
