import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from database import init_db
from models import Customer, Invoice, Profile, SummaryInvoiceCreate, SummaryInvoiceLink
from services import create_summary_invoice


@pytest.fixture(scope="session")
def engine():
    # Eine gemeinsame In-Memory-DB für alle Tests in dieser Datei
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # SQLite: FK-Enforcement aktivieren
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Tabellen laut Models anlegen (wird nach Implementierung grün)
    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def test_tables_exist_in_metadata():
    # Prüft, ob die Tabellen-Namen in den SQLModel-Metadaten registriert sind
    tables = SQLModel.metadata.tables
    assert "profile" in tables
    assert "invoice" in tables
    assert "invoice_item" in tables
    assert "summary_invoice" in tables
    assert "summary_invoice_link" in tables


def test_create_summary_invoice_calculations(session: Session):

    profile = Profile(
        name="Testprofil",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add(profile)
    session.add(customer)
    session.commit()

    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=False,
        tax_rate=0.19,
        total_amount=100.0,
    )
    session.add_all([inv1, inv2])
    session.commit()
    summary = SummaryInvoiceCreate(
        profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
    )
    # Act
    summary = create_summary_invoice(session, summary=summary)

    # Assert
    assert summary.total_net == pytest.approx(200.0, abs=0.1)
    assert summary.total_gross == pytest.approx(238.0, abs=0.1)
    assert "25 | 0001" in summary.range_text and "25 | 0002" in summary.range_text
    assert "25 | 0001 - 25 | 0002" == summary.range_text

    links = session.exec(
        select(SummaryInvoiceLink).filter_by(summary_invoice_id=summary.id)
    ).all()
    assert len(links) == 2


# POSITIVE EDGE CASES


def test_create_summary_invoice_single_invoice(session: Session):
    """Test creating summary invoice with only one invoice."""
    profile = Profile(
        name="Testprofil",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    invoice = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    session.add(invoice)
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(profile_id=profile.id, invoice_ids=[invoice.id]),
    )

    assert summary.total_net == pytest.approx(100.0, abs=0.1)
    assert summary.total_gross == pytest.approx(119.0, abs=0.1)
    assert summary.range_text == "25 | 0001 - 25 | 0001"


def test_create_summary_invoice_no_tax_kleinunternehmer(session: Session):
    """Test summary invoice for Kleinunternehmer (no tax)."""
    profile = Profile(
        name="Kleinunternehmer",
        address="X",
        city="Y",
        include_tax=False,
        default_tax_rate=0.0,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=False,
        is_gross_amount=True,
        tax_rate=0.0,
        total_amount=100.0,
    )
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=False,
        is_gross_amount=True,
        tax_rate=0.0,
        total_amount=200.0,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    assert summary.total_net == pytest.approx(300.0, abs=0.1)
    assert summary.total_tax == pytest.approx(0.0, abs=0.1)
    assert summary.total_gross == pytest.approx(300.0, abs=0.1)


def test_create_summary_invoice_mixed_tax_rates(session: Session):
    """Test summary invoice with different tax rates."""
    profile = Profile(
        name="Mixed Tax", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    # 19% Steuer
    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=False,
        tax_rate=0.19,
        total_amount=100.0,
    )
    # 7% Steuer (ermäßigt)
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=False,
        tax_rate=0.07,
        total_amount=100.0,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    assert summary.total_net == pytest.approx(200.0, abs=0.1)
    assert summary.total_tax == pytest.approx(26.0, abs=0.1)  # 19 + 7
    assert summary.total_gross == pytest.approx(226.0, abs=0.1)


def test_create_summary_invoice_mixed_gross_net_amounts(session: Session):
    """Test summary invoice with mixed gross and net amounts."""
    profile = Profile(
        name="Mixed Amounts",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    # Bruttobetrag
    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    # Nettobetrag
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=False,
        tax_rate=0.19,
        total_amount=100.0,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    assert summary.total_net == pytest.approx(200.0, abs=0.1)
    assert summary.total_tax == pytest.approx(38.0, abs=0.1)
    assert summary.total_gross == pytest.approx(238.0, abs=0.1)


def test_create_summary_invoice_large_number_range(session: Session):
    """Test summary invoice with large invoice number range."""
    profile = Profile(
        name="Large Range",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    inv1 = Invoice(
        number="25 | 0005",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    inv2 = Invoice(
        number="25 | 0050",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    assert summary.range_text == "25 | 0005 - 25 | 0050"


def test_create_summary_invoice_unordered_invoice_numbers(session: Session):
    """Test summary invoice with unordered invoice numbers."""
    profile = Profile(
        name="Unordered", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    # Rechnungen in ungeordneter Reihenfolge
    inv1 = Invoice(
        number="25 | 0030",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    inv2 = Invoice(
        number="25 | 0010",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    inv3 = Invoice(
        number="25 | 0020",
        date="2025-10-03",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    session.add_all([inv1, inv2, inv3])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id, inv3.id]
        ),
    )

    assert summary.range_text == "25 | 0010 - 25 | 0030"


# NEGATIVE EDGE CASES


def test_create_summary_invoice_invalid_profile_id(session: Session):
    """Test error when profile doesn't exist."""
    with pytest.raises(ValueError, match="Profile not found"):
        create_summary_invoice(
            session, summary=SummaryInvoiceCreate(profile_id=9999, invoice_ids=[1, 2])
        )


def test_create_summary_invoice_empty_invoice_list(session: Session):
    """Test error when invoice list is empty."""
    profile = Profile(
        name="Empty List",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    session.add(profile)
    session.commit()

    from pydantic import ValidationError

    with pytest.raises(
        ValidationError, match="At least one invoice ID must be provided"
    ):
        create_summary_invoice(
            session, summary=SummaryInvoiceCreate(profile_id=profile.id, invoice_ids=[])
        )


def test_create_summary_invoice_nonexistent_invoice_ids(session: Session):
    """Test error when invoice IDs don't exist."""
    profile = Profile(
        name="Nonexistent",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    session.add(profile)
    session.commit()

    with pytest.raises(ValueError, match="No valid invoices found"):
        create_summary_invoice(
            session,
            summary=SummaryInvoiceCreate(
                profile_id=profile.id, invoice_ids=[9999, 8888]
            ),
        )


def test_create_summary_invoice_wrong_profile_invoices(session: Session):
    """Test error when invoices belong to different profile."""
    profile1 = Profile(
        name="Profile 1", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    profile2 = Profile(
        name="Profile 2", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile1, profile2, customer])
    session.commit()

    # Invoice gehört zu profile2, aber wir versuchen summary für profile1 zu erstellen
    invoice = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile2.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    session.add(invoice)
    session.commit()

    with pytest.raises(ValueError, match="No valid invoices found"):
        create_summary_invoice(
            session,
            summary=SummaryInvoiceCreate(
                profile_id=profile1.id, invoice_ids=[invoice.id]
            ),
        )


def test_create_summary_invoice_partial_invalid_invoices(session: Session):
    """Test behavior when some invoices are valid and some invalid."""
    profile1 = Profile(
        name="Profile 1", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    profile2 = Profile(
        name="Profile 2", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile1, profile2, customer])
    session.commit()

    # Eine gültige Invoice für profile1
    valid_invoice = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile1.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    # Eine ungültige Invoice für profile2
    invalid_invoice = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile2.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    session.add_all([valid_invoice, invalid_invoice])
    session.commit()

    # Sollte nur die gültige Invoice verarbeiten
    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile1.id, invoice_ids=[valid_invoice.id, invalid_invoice.id]
        ),
    )

    assert summary.total_net == pytest.approx(100.0, abs=0.1)
    assert summary.range_text == "25 | 0001 - 25 | 0001"

    # Nur ein Link sollte erstellt werden
    links = session.exec(
        select(SummaryInvoiceLink).filter_by(summary_invoice_id=summary.id)
    ).all()
    assert len(links) == 1


def test_create_summary_invoice_zero_amounts(session: Session):
    """Test summary invoice with zero amounts."""
    profile = Profile(
        name="Zero Amounts",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    invoice = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=0.0,
    )
    session.add(invoice)
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(profile_id=profile.id, invoice_ids=[invoice.id]),
    )

    assert summary.total_net == pytest.approx(0.0, abs=0.1)
    assert summary.total_tax == pytest.approx(0.0, abs=0.1)
    assert summary.total_gross == pytest.approx(0.0, abs=0.1)


def test_create_summary_invoice_negative_amounts(session: Session):
    """Test summary invoice with negative amounts (Storno/Gutschrift)."""
    profile = Profile(
        name="Negative Amounts",
        address="X",
        city="Y",
        include_tax=True,
        default_tax_rate=0.19,
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    # Positive Rechnung
    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=119.0,
    )
    # Storno/Gutschrift
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=-59.5,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    assert summary.total_net == pytest.approx(50.0, abs=0.1)
    assert summary.total_gross == pytest.approx(59.5, abs=0.1)


def test_create_summary_invoice_very_high_tax_rate(session: Session):
    """Test summary invoice with unusually high tax rate."""
    profile = Profile(
        name="High Tax", address="X", city="Y", include_tax=True, default_tax_rate=0.5
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    invoice = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=False,
        tax_rate=0.5,
        total_amount=100.0,
    )  # 50% Steuer
    session.add(invoice)
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(profile_id=profile.id, invoice_ids=[invoice.id]),
    )

    assert summary.total_net == pytest.approx(100.0, abs=0.1)
    assert summary.total_tax == pytest.approx(50.0, abs=0.1)
    assert summary.total_gross == pytest.approx(150.0, abs=0.1)


def test_create_summary_invoice_rounding_precision(session: Session):
    """Test summary invoice rounding with very precise amounts."""
    profile = Profile(
        name="Precision", address="X", city="Y", include_tax=True, default_tax_rate=0.19
    )
    customer = Customer(name="Max Mustermann")
    session.add_all([profile, customer])
    session.commit()

    # Beträge die zu Rundungsfehlern führen können
    inv1 = Invoice(
        number="25 | 0001",
        date="2025-10-01",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=33.33,
    )
    inv2 = Invoice(
        number="25 | 0002",
        date="2025-10-02",
        profile_id=profile.id,
        customer_id=customer.id,
        include_tax=True,
        is_gross_amount=True,
        tax_rate=0.19,
        total_amount=66.67,
    )
    session.add_all([inv1, inv2])
    session.commit()

    summary = create_summary_invoice(
        session,
        summary=SummaryInvoiceCreate(
            profile_id=profile.id, invoice_ids=[inv1.id, inv2.id]
        ),
    )

    # Ergebnis sollte korrekt gerundet sein
    assert summary.total_gross == pytest.approx(100.0, abs=0.01)
    assert summary.total_net == pytest.approx(84.03, abs=0.01)
    assert summary.total_tax == pytest.approx(15.97, abs=0.01)
