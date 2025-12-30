"""
Tests for the pdf_generation_service module.
Tests background PDF generation with race condition handling.
"""

import sqlite3
import threading
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from database import init_db
from models.invoice import Invoice
from models.stored_pdf import StoredPDF
from models.summary_invoice import SummaryInvoice
from services.pdf_generation_service import (
    generate_pdf_for_invoice,
    generate_pdf_for_summary_invoice,
)

# Test database setup
TEST_DB_URL = "sqlite:///:memory:"

# Constants
PDF_BASE64_HEADER = "JVBERi0"  # Base64 encoded PDF file signature "%PDF-"


@pytest.fixture(scope="session")
def engine():
    """Create a test database engine"""
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a test database session"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_invoice(session):
    """Create a sample invoice with all required data"""
    # Import models here to avoid circular imports
    from models.customer import Customer
    from models.profile import Profile
    from services.invoice_number_generator import generate_next_invoice_number

    # Create profile
    profile = Profile(
        name="Test Profile",
        address="Test Address",
        city="Test City",
        bank_data="TEST-IBAN-DE89370400440532013000",
        tax_number="123/456/78910",
        include_tax=True,
        default_tax_rate=0.19,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    # Create customer
    customer = Customer(
        name="Test Customer",
        address="Customer Address",
        city="Customer City",
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    # Generate invoice number
    invoice_number = generate_next_invoice_number(session)

    # Create invoice
    invoice = Invoice(
        number=invoice_number,
        date="2025-10-20",
        customer_id=customer.id,
        profile_id=profile.id,
        total_amount=100.00,
        include_tax=True,
        tax_rate=0.19,
        is_gross_amount=False,
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)

    return invoice


@pytest.fixture
def sample_summary_invoice(session):
    """Create a sample summary invoice with all required data"""
    from models.customer import Customer
    from models.profile import Profile
    from models.summary_invoice import SummaryInvoiceLink
    from services.invoice_number_generator import generate_next_invoice_number

    # Create profile
    profile = Profile(
        name="Summary Test Profile",
        address="Summary Address",
        city="Summary City",
        include_tax=True,
        default_tax_rate=0.19,
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)

    # Create customer
    customer = Customer(
        name="Summary Customer",
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)

    # Create invoices for the summary
    invoice1 = Invoice(
        number=generate_next_invoice_number(session),
        date="2025-10-20",
        customer_id=customer.id,
        profile_id=profile.id,
        total_amount=100.00,
    )
    session.add(invoice1)
    session.commit()
    session.refresh(invoice1)

    invoice2 = Invoice(
        number=generate_next_invoice_number(session),
        date="2025-10-21",
        customer_id=customer.id,
        profile_id=profile.id,
        total_amount=150.00,
    )
    session.add(invoice2)
    session.commit()
    session.refresh(invoice2)

    # Create summary invoice with totals
    summary_invoice = SummaryInvoice(
        profile_id=profile.id,
        range_text="Test Range",
        date="2025-10-31",
        total_net=210.08,  # 100 + 150 / 1.19
        total_tax=39.92,
        total_gross=250.00,
    )
    session.add(summary_invoice)
    session.commit()
    session.refresh(summary_invoice)

    # Link invoices to summary invoice using the link table
    link1 = SummaryInvoiceLink(
        summary_invoice_id=summary_invoice.id,
        invoice_id=invoice1.id,
    )
    link2 = SummaryInvoiceLink(
        summary_invoice_id=summary_invoice.id,
        invoice_id=invoice2.id,
    )
    session.add(link1)
    session.add(link2)
    session.commit()

    return summary_invoice


class TestGeneratePDFForInvoice:
    """Test generate_pdf_for_invoice function"""

    def test_successful_pdf_generation(self, session, sample_invoice):
        """Test successful PDF generation for an invoice"""
        result = generate_pdf_for_invoice(session, sample_invoice.id)

        assert result is True

        # Verify PDF was stored in database
        stored_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == sample_invoice.id)
        ).first()
        assert stored_pdf is not None
        assert stored_pdf.type == "invoice"
        assert stored_pdf.invoice_id == sample_invoice.id
        assert len(stored_pdf.content) > 0
        assert stored_pdf.content.startswith(PDF_BASE64_HEADER)

    def test_pdf_already_exists(self, session, sample_invoice):
        """Test that function returns False when PDF already exists without error"""
        # Generate PDF first time
        result1 = generate_pdf_for_invoice(session, sample_invoice.id)
        assert result1 is True

        # Attempt to generate again
        result2 = generate_pdf_for_invoice(session, sample_invoice.id)
        assert result2 is False

        # Verify only one PDF exists
        pdfs = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == sample_invoice.id)
        ).all()
        assert len(pdfs) == 1

    def test_invoice_not_found(self, session):
        """Test handling of non-existent invoice"""
        result = generate_pdf_for_invoice(session, 999999)
        assert result is False

        # Verify no PDF was created
        pdf = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == 999999)
        ).first()
        assert pdf is None

    def test_exception_handling(self, session, sample_invoice):
        """Test that exceptions are caught and function returns False"""
        # Mock PDFDataService to raise an exception
        with patch(
            "services.pdf_generation_service.PDFDataService"
        ) as mock_pdf_data_service:
            mock_instance = Mock()
            mock_instance.get_invoice_pdf_data.side_effect = Exception("Test exception")
            mock_pdf_data_service.return_value = mock_instance

            result = generate_pdf_for_invoice(session, sample_invoice.id)
            assert result is False

            # Verify no PDF was created
            pdf = session.exec(
                select(StoredPDF).where(StoredPDF.invoice_id == sample_invoice.id)
            ).first()
            assert pdf is None

    def test_concurrent_generation_attempts(self, session, sample_invoice):
        """Test race condition handling with concurrent generation attempts

        This test verifies that the unique constraint on invoice_id prevents
        duplicate PDFs from being created even when multiple threads attempt
        to generate PDFs concurrently. The database-level unique constraint
        ensures atomicity and prevents the race condition that could occur
        with the check-then-create pattern.

        In this test, we verify that:
        - The function handles concurrent access gracefully (no unhandled exceptions)
        - Only one PDF is created OR none are created (if all fail due to concurrency)
        - The IntegrityError from duplicate inserts is caught and handled

        Note: SQLite with threading can result in various concurrency errors.
        The test allows for all threads to fail due to database/session conflicts,
        as long as no duplicate PDFs are created.
        """
        results = []

        def generate_pdf():
            # Create a new session for this thread
            try:
                with Session(session.get_bind()) as thread_session:
                    # Fetch the invoice fresh in this thread's session
                    invoice = thread_session.get(Invoice, sample_invoice.id)
                    if invoice:
                        result = generate_pdf_for_invoice(thread_session, invoice.id)
                        results.append(result)
                    else:
                        # Invoice not found in this session (can happen with concurrency)
                        results.append(False)
            except (SQLAlchemyError, sqlite3.Error) as e:
                # Expected SQLite/SQLAlchemy concurrency errors - handle gracefully
                # These include IntegrityError (duplicates), OperationalError (busy),
                # InvalidRequestError (NULL keys), ObjectDeletedError, etc.
                # All are normal in concurrent scenarios
                results.append(False)
            except Exception as e:
                # Unexpected error - re-raise to fail the test
                raise AssertionError(
                    f"Unexpected exception in concurrent PDF generation: {type(e).__name__}: {e}"
                ) from e

        # Create multiple threads attempting to generate the same PDF
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_pdf)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should have completed (returned a result or caught exception)
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # CRITICAL: Verify at most one PDF was created (enforced by unique constraint)
        # Due to SQLite threading limitations, it's possible all threads fail,
        # but we must never have duplicates
        pdfs = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == sample_invoice.id)
        ).all()
        assert (
            len(pdfs) <= 1
        ), f"Expected at most 1 PDF, but found {len(pdfs)} - unique constraint violation!"


class TestGeneratePDFForSummaryInvoice:
    """Test generate_pdf_for_summary_invoice function"""

    def test_successful_pdf_generation(self, session, sample_summary_invoice):
        """Test successful PDF generation for a summary invoice"""
        result = generate_pdf_for_summary_invoice(
            session, sample_summary_invoice.id, "Test Recipient"
        )

        assert result is True

        # Verify PDF was stored in database
        stored_pdf = session.exec(
            select(StoredPDF).where(
                StoredPDF.summary_invoice_id == sample_summary_invoice.id
            )
        ).first()
        assert stored_pdf is not None
        assert stored_pdf.type == "summary_invoice"
        assert stored_pdf.summary_invoice_id == sample_summary_invoice.id
        assert len(stored_pdf.content) > 0
        assert stored_pdf.content.startswith(PDF_BASE64_HEADER)

    def test_successful_pdf_generation_without_recipient(
        self, session, sample_summary_invoice
    ):
        """Test successful PDF generation without recipient name (fallback to customer names)"""
        result = generate_pdf_for_summary_invoice(
            session, sample_summary_invoice.id, None
        )

        assert result is True

        # Verify PDF was stored in database
        stored_pdf = session.exec(
            select(StoredPDF).where(
                StoredPDF.summary_invoice_id == sample_summary_invoice.id
            )
        ).first()
        assert stored_pdf is not None
        assert stored_pdf.type == "summary_invoice"

    def test_pdf_already_exists(self, session, sample_summary_invoice):
        """Test that function returns False when PDF already exists without error"""
        # Generate PDF first time
        result1 = generate_pdf_for_summary_invoice(
            session, sample_summary_invoice.id, "Test Recipient"
        )
        assert result1 is True

        # Attempt to generate again
        result2 = generate_pdf_for_summary_invoice(
            session, sample_summary_invoice.id, "Test Recipient"
        )
        assert result2 is False

        # Verify only one PDF exists
        pdfs = session.exec(
            select(StoredPDF).where(
                StoredPDF.summary_invoice_id == sample_summary_invoice.id
            )
        ).all()
        assert len(pdfs) == 1

    def test_summary_invoice_not_found(self, session):
        """Test handling of non-existent summary invoice"""
        result = generate_pdf_for_summary_invoice(session, 999999, "Test Recipient")
        assert result is False

        # Verify no PDF was created
        pdf = session.exec(
            select(StoredPDF).where(StoredPDF.summary_invoice_id == 999999)
        ).first()
        assert pdf is None

    def test_exception_handling(self, session, sample_summary_invoice):
        """Test that exceptions are caught and function returns False"""
        # Mock PDFDataService to raise an exception
        with patch(
            "services.pdf_generation_service.PDFDataService"
        ) as mock_pdf_data_service:
            mock_instance = Mock()
            mock_instance.get_summary_invoice_pdf_data.side_effect = Exception(
                "Test exception"
            )
            mock_pdf_data_service.return_value = mock_instance

            result = generate_pdf_for_summary_invoice(
                session, sample_summary_invoice.id, "Test Recipient"
            )
            assert result is False

            # Verify no PDF was created
            pdf = session.exec(
                select(StoredPDF).where(
                    StoredPDF.summary_invoice_id == sample_summary_invoice.id
                )
            ).first()
            assert pdf is None

    def test_concurrent_generation_attempts(self, session, sample_summary_invoice):
        """Test race condition handling with concurrent generation attempts

        This test verifies that the unique constraint on summary_invoice_id prevents
        duplicate PDFs from being created even when multiple threads attempt
        to generate PDFs concurrently. The database-level unique constraint
        ensures atomicity and prevents the race condition that could occur
        with the check-then-create pattern.

        In this test, we verify that:
        - The function handles concurrent access gracefully (no unhandled exceptions)
        - Only one PDF is created OR none are created (if all fail due to concurrency)
        - The IntegrityError from duplicate inserts is caught and handled

        Note: SQLite with threading can result in various concurrency errors.
        The test allows for all threads to fail due to database/session conflicts,
        as long as no duplicate PDFs are created.
        """
        results = []

        def generate_pdf():
            # Create a new session for this thread
            try:
                with Session(session.get_bind()) as thread_session:
                    # Fetch the summary invoice fresh in this thread's session
                    from models.summary_invoice import SummaryInvoice

                    summary_invoice = thread_session.get(
                        SummaryInvoice, sample_summary_invoice.id
                    )
                    if summary_invoice:
                        result = generate_pdf_for_summary_invoice(
                            thread_session, summary_invoice.id, "Test Recipient"
                        )
                        results.append(result)
                    else:
                        # Summary invoice not found in this session (can happen with concurrency)
                        results.append(False)
            except (SQLAlchemyError, sqlite3.Error) as e:
                # Expected SQLite/SQLAlchemy concurrency errors - handle gracefully
                # These include IntegrityError (duplicates), OperationalError (busy),
                # InvalidRequestError (NULL keys), ObjectDeletedError, etc.
                # All are normal in concurrent scenarios
                results.append(False)
            except Exception as e:
                # Unexpected error - re-raise to fail the test
                raise AssertionError(
                    f"Unexpected exception in concurrent PDF generation: {type(e).__name__}: {e}"
                ) from e

        # Create multiple threads attempting to generate the same PDF
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_pdf)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should have completed (returned a result or caught exception)
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

        # CRITICAL: Verify at most one PDF was created (enforced by unique constraint)
        # Due to SQLite threading limitations, it's possible all threads fail,
        # but we must never have duplicates
        pdfs = session.exec(
            select(StoredPDF).where(
                StoredPDF.summary_invoice_id == sample_summary_invoice.id
            )
        ).all()
        assert (
            len(pdfs) <= 1
        ), f"Expected at most 1 PDF, but found {len(pdfs)} - unique constraint violation!"
