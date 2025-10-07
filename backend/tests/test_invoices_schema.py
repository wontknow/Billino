# backend/tests/test_invoices_schema.py
import pytest
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from database import init_db


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
        include_tax=False,          # <— hier statt True auch mal False testen
        tax_rate=0.07,              # <— neuer Wert
        is_gross_amount=False,      # <— neuer Wert
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
