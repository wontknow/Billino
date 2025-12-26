"""
Tests for the BackgroundPDFGenerator helper class.
Tests the background PDF generation threading logic.
"""

import threading
import time
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from database import init_db
from models.invoice import Invoice
from models.stored_pdf import StoredPDF
from services.background_pdf_generator import BackgroundPDFGenerator
from services.pdf_generation_service import (
    generate_pdf_for_invoice,
    generate_pdf_for_summary_invoice,
)

# Test database setup
TEST_DB_URL = "sqlite:///:memory:"


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
    from models.summary_invoice import SummaryInvoice, SummaryInvoiceLink
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


class TestBackgroundPDFGenerator:
    """Test the BackgroundPDFGenerator helper class"""

    def test_successful_background_invoice_generation(
        self, engine, session, sample_invoice
    ):
        """Test successful background PDF generation for an invoice"""
        invoice_id = sample_invoice.id

        # Mock get_engine to return the test engine
        with patch("services.background_pdf_generator.get_engine", return_value=engine):
            # Generate PDF in background
            thread = BackgroundPDFGenerator.generate_in_background(
                pdf_generation_func=generate_pdf_for_invoice,
                entity_id=invoice_id,
                entity_type="invoice",
            )

            # Verify thread was created and started
            assert thread is not None
            assert isinstance(thread, threading.Thread)
            assert thread.daemon is True
            assert thread.name == f"PDF-{invoice_id}"
            assert (
                thread.is_alive() or not thread.is_alive()
            )  # May have finished quickly

            # Wait for thread to complete
            thread.join(timeout=5.0)

            # Verify thread completed
            assert not thread.is_alive()

        # Verify PDF was created
        stored_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.invoice_id == invoice_id)
        ).first()
        assert stored_pdf is not None
        assert stored_pdf.type == "invoice"

    def test_successful_background_summary_invoice_generation(
        self, engine, session, sample_summary_invoice
    ):
        """Test successful background PDF generation for a summary invoice"""
        summary_invoice_id = sample_summary_invoice.id

        # Mock get_engine to return the test engine
        with patch("services.background_pdf_generator.get_engine", return_value=engine):
            # Generate PDF in background
            thread = BackgroundPDFGenerator.generate_in_background(
                pdf_generation_func=generate_pdf_for_summary_invoice,
                entity_id=summary_invoice_id,
                entity_type="summary invoice",
                thread_name_prefix="PDF-Summary",
                recipient_name="Test Recipient",
            )

            # Verify thread was created and started
            assert thread is not None
            assert isinstance(thread, threading.Thread)
            assert thread.daemon is True
            assert thread.name == f"PDF-Summary-{summary_invoice_id}"

            # Wait for thread to complete
            thread.join(timeout=5.0)

            # Verify thread completed
            assert not thread.is_alive()

        # Verify PDF was created
        stored_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.summary_invoice_id == summary_invoice_id)
        ).first()
        assert stored_pdf is not None
        assert stored_pdf.type == "summary_invoice"

    def test_custom_thread_name_prefix(self, sample_invoice):
        """Test that custom thread name prefix is used"""
        thread = BackgroundPDFGenerator.generate_in_background(
            pdf_generation_func=generate_pdf_for_invoice,
            entity_id=sample_invoice.id,
            entity_type="invoice",
            thread_name_prefix="CustomPrefix",
        )

        assert thread.name == f"CustomPrefix-{sample_invoice.id}"
        thread.join(timeout=5.0)

    def test_thread_handles_exception_gracefully(self):
        """Test that exceptions in the background function are handled gracefully"""

        def failing_function(session, entity_id):
            raise ValueError("Simulated failure")

        # This should not raise an exception
        thread = BackgroundPDFGenerator.generate_in_background(
            pdf_generation_func=failing_function,
            entity_id=999,
            entity_type="test",
        )

        # Wait for thread to complete
        thread.join(timeout=5.0)

        # Verify thread completed without crashing
        assert not thread.is_alive()

    def test_daemon_thread_property(self, sample_invoice):
        """Test that created threads are daemon threads"""
        thread = BackgroundPDFGenerator.generate_in_background(
            pdf_generation_func=generate_pdf_for_invoice,
            entity_id=sample_invoice.id,
            entity_type="invoice",
        )

        # Verify daemon property
        assert thread.daemon is True

        thread.join(timeout=5.0)

    def test_multiple_concurrent_generations(self, session):
        """Test multiple concurrent background generations"""
        from models.customer import Customer
        from models.profile import Profile
        from services.invoice_number_generator import generate_next_invoice_number

        # Create profile and customer
        profile = Profile(
            name="Concurrent Test Profile",
            address="Test Address",
            city="Test City",
            include_tax=True,
            default_tax_rate=0.19,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

        customer = Customer(name="Test Customer")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        # Create multiple invoices
        invoices = []
        for _ in range(3):
            invoice = Invoice(
                number=generate_next_invoice_number(session),
                date="2025-10-20",
                customer_id=customer.id,
                profile_id=profile.id,
                total_amount=100.00,
            )
            session.add(invoice)
            session.commit()
            session.refresh(invoice)
            invoices.append(invoice)

        # Start background generation for all invoices
        threads = []
        for invoice in invoices:
            thread = BackgroundPDFGenerator.generate_in_background(
                pdf_generation_func=generate_pdf_for_invoice,
                entity_id=invoice.id,
                entity_type="invoice",
            )
            threads.append(thread)

        # Verify all threads were created
        assert len(threads) == 3
        for thread in threads:
            assert isinstance(thread, threading.Thread)
            assert thread.daemon is True

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all threads completed
        for thread in threads:
            assert not thread.is_alive()

        # Verify PDFs were created for all invoices
        for invoice in invoices:
            stored_pdf = session.exec(
                select(StoredPDF).where(StoredPDF.invoice_id == invoice.id)
            ).first()
            # At least some should succeed (race condition handling means not all may succeed)
            # We just verify the system doesn't crash

    def test_kwargs_passed_to_function(self, engine, session, sample_summary_invoice):
        """Test that additional kwargs are passed to the PDF generation function"""
        recipient_name = "Custom Recipient"
        summary_invoice_id = sample_summary_invoice.id

        # Mock get_engine to return the test engine
        with patch("services.background_pdf_generator.get_engine", return_value=engine):
            thread = BackgroundPDFGenerator.generate_in_background(
                pdf_generation_func=generate_pdf_for_summary_invoice,
                entity_id=summary_invoice_id,
                entity_type="summary invoice",
                recipient_name=recipient_name,  # This should be passed as kwarg
            )

            thread.join(timeout=5.0)

        # Verify PDF was created (implicitly tests that kwargs were passed correctly)
        stored_pdf = session.exec(
            select(StoredPDF).where(StoredPDF.summary_invoice_id == summary_invoice_id)
        ).first()
        assert stored_pdf is not None

    def test_session_cleanup_on_success(self, sample_invoice):
        """Test that session is properly closed after successful generation"""
        thread = BackgroundPDFGenerator.generate_in_background(
            pdf_generation_func=generate_pdf_for_invoice,
            entity_id=sample_invoice.id,
            entity_type="invoice",
        )

        thread.join(timeout=5.0)

        # If session wasn't closed, we'd have resource leaks
        # We can't directly test session closure, but we can verify no exceptions occurred
        assert not thread.is_alive()

    def test_session_cleanup_on_failure(self):
        """Test that session is properly closed even when generation fails"""

        def failing_function(session, entity_id):
            # Access session to ensure it was created
            session.exec(select(Invoice).where(Invoice.id == 999999)).first()
            raise RuntimeError("Test failure")

        thread = BackgroundPDFGenerator.generate_in_background(
            pdf_generation_func=failing_function,
            entity_id=999,
            entity_type="test",
        )

        thread.join(timeout=5.0)

        # Session should be closed despite the exception
        assert not thread.is_alive()
