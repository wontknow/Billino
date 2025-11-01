# backend/tests/test_invoices_schema.py
import pytest
from database import init_db
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select


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


def test_insert_with_foreign_keys(session: Session):
    """
    Happy Path:
    - Customer + Profile anlegen
    - Invoice referenziert beide
    - InvoiceItem referenziert Invoice
    - Alles committen und wieder auslesen
    """
    # Lazy-Import, damit Tests schon vor Implementierung geladen werden
    from models.customer import Customer
    from models.invoice import Invoice
    from models.invoice_item import InvoiceItem
    from models.profile import Profile

    cust = Customer(name="Max Mustermann")
    prof = Profile(
        name="Salon Sunshine",
        address="Hauptstr. 1",
        city="12345 Berlin",
        bank_data="DE00 1234 5678 9000 0000 00",
        tax_number="12/345/67890",
    )
    session.add(cust)
    session.add(prof)
    session.commit()
    session.refresh(cust)
    session.refresh(prof)

    inv = Invoice(
        number="25|00001",
        date="2025-09-01",
        customer_id=cust.id,
        profile_id=prof.id,
        include_tax=False,  # <— hier statt True auch mal False testen
        tax_rate=0.07,  # <— neuer Wert
        is_gross_amount=False,  # <— neuer Wert
        total_amount=49.90,
    )
    session.add(inv)
    session.commit()
    session.refresh(inv)

    item = InvoiceItem(
        invoice_id=inv.id,
        quantity=1,
        description="Haarschnitt Damen",
        price=49.90,
    )
    session.add(item)
    session.commit()
    session.refresh(item)

    # Verifizieren
    loaded_inv = session.exec(select(Invoice).where(Invoice.id == inv.id)).one()
    assert loaded_inv.customer_id == cust.id
    assert loaded_inv.profile_id == prof.id
    assert inv.include_tax is False
    assert inv.tax_rate == 0.07
    assert inv.is_gross_amount is False

    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)
    ).all()
    assert len(items) == 1
    assert items[0].description == "Haarschnitt Damen"


def test_foreign_key_enforced(session: Session):
    """
    Negative Case:
    Versuche eine Invoice mit nicht existierender customer_id/profile_id anzulegen.
    Erwartet: IntegrityError (FK-Verletzung)
    """
    from models.invoice import Invoice

    bad_invoice = Invoice(
        number="25|99999",
        date="2025-09-01",
        customer_id=999999,  # existiert nicht
        profile_id=999999,  # existiert nicht
        include_tax=True,
        total_amount=10.0,
    )
    session.add(bad_invoice)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# summary_invoice tests


def test_summary_invoice_tables_exist_in_metadata():
    # Prüft, ob die Tabellen-Namen in den SQLModel-Metadaten registriert sind
    tables = SQLModel.metadata.tables
    assert "summary_invoice" in tables
    assert "summary_invoice_link" in tables


def test_insert_summary_invoice_with_links(session: Session):
    """
    Happy Path:
    - Profile anlegen
    - SummaryInvoice referenziert Profile
    - SummaryInvoiceLink referenziert SummaryInvoice und Invoice
    - Alles committen und wieder auslesen
    """
    # Lazy-Import, damit Tests schon vor Implementierung geladen werden
    from models.invoice import Invoice
    from models.profile import Profile
    from models.summary_invoice import SummaryInvoice, SummaryInvoiceLink

    prof = Profile(
        name="Salon Sunshine",
        address="Hauptstr. 1",
        city="12345 Berlin",
        bank_data="DE00 1234 5678 9000 0000 00",
        tax_number="12/345/67890",
    )
    session.add(prof)
    session.commit()
    session.refresh(prof)

    # Dummy-Invoice anlegen, die verlinkt wird
    inv = Invoice(
        number="25|00002",
        date="2025-09-02",
        customer_id=1,  # FK ignorieren wir hier
        profile_id=prof.id,
        include_tax=False,
        tax_rate=0.07,
        is_gross_amount=False,
        total_amount=59.90,
    )
    inv2 = Invoice(
        number="25|00003",
        date="2025-09-03",
        customer_id=1,  # FK ignorieren wir hier
        profile_id=prof.id,
        include_tax=False,
        tax_rate=0.07,
        is_gross_amount=False,
        total_amount=79.90,
    )
    session.add(inv)
    session.add(inv2)
    session.commit()
    session.refresh(inv)
    session.refresh(inv2)

    summ_inv = SummaryInvoice(
        range_text="25|00002 - 25|00003",
        date="2025-09-30",
        profile_id=prof.id,
        total_net=139.80,
        total_tax=9.79,
        total_gross=149.59,
    )

    session.add(summ_inv)
    session.commit()
    session.refresh(summ_inv)

    link = SummaryInvoiceLink(
        summary_invoice_id=summ_inv.id,
        invoice_id=inv.id,
    )
    link2 = SummaryInvoiceLink(
        summary_invoice_id=summ_inv.id,
        invoice_id=inv2.id,
    )
    session.add(link)
    session.add(link2)
    session.commit()
    session.refresh(link)

    # Verifizieren
    loaded_summ_inv = session.exec(
        select(SummaryInvoice).where(SummaryInvoice.id == summ_inv.id)
    ).one()
    assert loaded_summ_inv.profile_id == prof.id

    links = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summ_inv.id
        )
    ).all()
    assert len(links) == 2
    assert links[0].invoice_id == inv.id
    assert links[1].invoice_id == inv2.id


def test_summary_invoice_foreign_key_enforced(session: Session):
    """
    Negative Case:
    Versuche eine SummaryInvoice mit nicht existierender profile_id anzulegen.
    Erwartet: IntegrityError (FK-Verletzung)
    """
    from models.summary_invoice import SummaryInvoice

    bad_summ_inv = SummaryInvoice(
        range_text="25|99999 - 25|99999",
        date="2025-09-30",
        profile_id=999999,  # existiert nicht
        total_net=100.0,
        total_tax=7.0,
        total_gross=107.0,
    )
    session.add(bad_summ_inv)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    """
    Negative Case:
    Versuche eine SummaryInvoiceLink mit nicht existierender summary_invoice_id/invoice_id anzulegen.
    Erwartet: IntegrityError (FK-Verletzung)
    """
    from models.summary_invoice import SummaryInvoiceLink

    bad_link = SummaryInvoiceLink(
        summary_invoice_id=999999,  # existiert nicht
        invoice_id=999999,  # existiert nicht
    )
    session.add(bad_link)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
