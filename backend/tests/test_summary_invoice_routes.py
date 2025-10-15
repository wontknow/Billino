import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from database import get_session, init_db
from main import app
from models import Customer, Invoice, Profile, SummaryInvoice, SummaryInvoiceLink

client = TestClient(app)


@pytest.fixture(scope="session")
def engine():
    """Test engine with in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    init_db(engine)
    return engine


@pytest.fixture
def session(engine):
    """Test session for each test."""
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    """Test client with dependency override."""

    def get_test_session():
        return session

    app.dependency_overrides[get_session] = get_test_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(session):
    """Create sample data for tests."""
    # Create profiles
    profile = Profile(
        name="Test Profile",
        address="Test Address",
        city="Test City",
        include_tax=True,
        default_tax_rate=0.19,
    )
    profile_no_tax = Profile(
        name="No Tax Profile",
        address="Test Address",
        city="Test City",
        include_tax=False,
        default_tax_rate=0.0,
    )

    # Create customer
    customer = Customer(
        name="Test Customer", address="Customer Address", city="Customer City"
    )

    session.add_all([profile, profile_no_tax, customer])
    session.commit()

    # Create invoices
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
    inv3 = Invoice(
        number="25 | 0003",
        date="2025-10-03",
        profile_id=profile_no_tax.id,
        customer_id=customer.id,
        include_tax=False,
        is_gross_amount=True,
        tax_rate=0.0,
        total_amount=50.0,
    )

    session.add_all([inv1, inv2, inv3])
    session.commit()

    return {
        "profile": profile,
        "profile_no_tax": profile_no_tax,
        "customer": customer,
        "invoices": [inv1, inv2, inv3],
    }


# =============================================================================
# HAPPY PATH TESTS - CREATE SUMMARY INVOICE
# =============================================================================


def test_create_summary_invoice_success(client, sample_data):
    """Test successful creation of summary invoice."""
    data = sample_data
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 201
    result = response.json()
    assert result["id"] is not None
    assert result["profile_id"] == data["profile"].id
    assert result["range_text"] == "25 | 0001 - 25 | 0002"
    assert result["total_net"] == pytest.approx(200.0, abs=0.01)
    assert result["total_tax"] == pytest.approx(38.0, abs=0.01)
    assert result["total_gross"] == pytest.approx(238.0, abs=0.01)
    assert "date" in result


def test_create_summary_invoice_single_invoice(client, sample_data):
    """Test creation with single invoice."""
    data = sample_data
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id],
    }

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 201
    result = response.json()
    assert result["range_text"] == "25 | 0001 - 25 | 0001"
    assert result["total_net"] == pytest.approx(100.0, abs=0.01)
    assert result["total_gross"] == pytest.approx(119.0, abs=0.01)


def test_create_summary_invoice_no_tax(client, sample_data):
    """Test creation with no-tax profile."""
    data = sample_data
    payload = {
        "profile_id": data["profile_no_tax"].id,
        "invoice_ids": [data["invoices"][2].id],
    }

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 201
    result = response.json()
    assert result["total_net"] == pytest.approx(50.0, abs=0.01)
    assert result["total_tax"] == pytest.approx(0.0, abs=0.01)
    assert result["total_gross"] == pytest.approx(50.0, abs=0.01)


# =============================================================================
# ERROR CASES - CREATE SUMMARY INVOICE
# =============================================================================


def test_create_summary_invoice_invalid_profile(client, sample_data):
    """Test creation with non-existent profile."""
    payload = {"profile_id": 9999, "invoice_ids": [1, 2]}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 400
    error = response.json()
    assert "detail" in error
    assert any("Profile not found" in str(detail) for detail in error["detail"])


def test_create_summary_invoice_empty_invoice_list(client, sample_data):
    """Test creation with empty invoice list."""
    data = sample_data
    payload = {"profile_id": data["profile"].id, "invoice_ids": []}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 400
    error = response.json()
    assert "detail" in error
    assert any("No valid invoices found" in str(detail) for detail in error["detail"])


def test_create_summary_invoice_nonexistent_invoices(client, sample_data):
    """Test creation with non-existent invoice IDs."""
    data = sample_data
    payload = {"profile_id": data["profile"].id, "invoice_ids": [9999, 8888]}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 400
    error = response.json()
    assert "detail" in error
    assert any("No valid invoices found" in str(detail) for detail in error["detail"])


def test_create_summary_invoice_wrong_profile_invoices(client, sample_data):
    """Test creation with invoices from different profile."""
    data = sample_data
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [
            data["invoices"][2].id
        ],  # This invoice belongs to profile_no_tax
    }

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 400
    error = response.json()
    assert "detail" in error
    assert any("No valid invoices found" in str(detail) for detail in error["detail"])


def test_create_summary_invoice_missing_profile_id(client):
    """Test creation with missing profile_id."""
    payload = {"invoice_ids": [1, 2]}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 422  # Validation error
    error = response.json()
    assert "detail" in error


def test_create_summary_invoice_missing_invoice_ids(client, sample_data):
    """Test creation with missing invoice_ids."""
    data = sample_data
    payload = {"profile_id": data["profile"].id}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 422  # Validation error
    error = response.json()
    assert "detail" in error


def test_create_summary_invoice_invalid_data_types(client):
    """Test creation with invalid data types."""
    payload = {"profile_id": "not_an_integer", "invoice_ids": ["not", "integers"]}

    response = client.post("/summary-invoices", json=payload)

    assert response.status_code == 422  # Validation error
    error = response.json()
    assert "detail" in error


# =============================================================================
# HAPPY PATH TESTS - READ SUMMARY INVOICES (LIST)
# =============================================================================


def test_get_summary_invoices_list_empty(client):
    """Test getting empty list of summary invoices."""
    response = client.get("/summary-invoices")

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 0


def test_get_summary_invoices_list_with_data(client, sample_data):
    """Test getting list of summary invoices with existing data."""
    data = sample_data

    # First create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    assert create_response.status_code == 201

    # Then get the list
    response = client.get("/summary-invoices")

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] is not None
    assert result[0]["profile_id"] == data["profile"].id
    assert result[0]["range_text"] == "25 | 0001 - 25 | 0002"


def test_get_summary_invoices_list_multiple(client, sample_data):
    """Test getting list with multiple summary invoices."""
    data = sample_data

    # Create multiple summary invoices
    payload1 = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id],
    }
    payload2 = {
        "profile_id": data["profile_no_tax"].id,
        "invoice_ids": [data["invoices"][2].id],
    }

    client.post("/summary-invoices", json=payload1)
    client.post("/summary-invoices", json=payload2)

    response = client.get("/summary-invoices")

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 2


def test_get_summary_invoices_list_by_profile(client, sample_data):
    """Test getting list filtered by profile."""
    data = sample_data

    # Create summary invoices for different profiles
    payload1 = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id],
    }
    payload2 = {
        "profile_id": data["profile_no_tax"].id,
        "invoice_ids": [data["invoices"][2].id],
    }

    client.post("/summary-invoices", json=payload1)
    client.post("/summary-invoices", json=payload2)

    # Filter by profile_id
    response = client.get(f"/invoices/summary?profile_id={data['profile'].id}")

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0]["profile_id"] == data["profile"].id


# =============================================================================
# HAPPY PATH TESTS - READ SUMMARY INVOICE (SINGLE)
# =============================================================================


def test_get_summary_invoice_by_id_success(client, sample_data):
    """Test getting single summary invoice by ID."""
    data = sample_data

    # Create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    # Get the summary invoice
    response = client.get(f"/invoices/summary/{summary_id}")

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == summary_id
    assert result["profile_id"] == data["profile"].id
    assert result["range_text"] == "25 | 0001 - 25 | 0002"
    assert "invoice_ids" in result
    assert len(result["invoice_ids"]) == 2


def test_get_summary_invoice_with_linked_invoices(client, sample_data):
    """Test getting summary invoice includes linked invoice IDs."""
    data = sample_data

    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    response = client.get(f"/invoices/summary/{summary_id}")

    assert response.status_code == 200
    result = response.json()
    assert "invoice_ids" in result
    assert set(result["invoice_ids"]) == {
        data["invoices"][0].id,
        data["invoices"][1].id,
    }


# =============================================================================
# ERROR CASES - READ SUMMARY INVOICE (SINGLE)
# =============================================================================


def test_get_summary_invoice_not_found(client):
    """Test getting non-existent summary invoice."""
    response = client.get("/invoices/summary/9999")

    assert response.status_code == 404
    error = response.json()
    assert "detail" in error
    assert any("not found" in str(detail).lower() for detail in error["detail"])


def test_get_summary_invoice_invalid_id(client):
    """Test getting summary invoice with invalid ID format."""
    response = client.get("/invoices/summary/not_an_integer")

    assert response.status_code == 422  # Validation error
    error = response.json()
    assert "detail" in error


# =============================================================================
# HAPPY PATH TESTS - DELETE SUMMARY INVOICE
# =============================================================================


def test_delete_summary_invoice_success(client, sample_data):
    """Test successful deletion of summary invoice."""
    data = sample_data

    # Create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    # Delete the summary invoice
    response = client.delete(f"/invoices/summary/{summary_id}")

    assert response.status_code == 204
    assert response.content == b""

    # Verify it's deleted
    get_response = client.get(f"/invoices/summary/{summary_id}")
    assert get_response.status_code == 404


def test_delete_summary_invoice_cascade_links(client, sample_data, session):
    """Test that deleting summary invoice also deletes links."""
    data = sample_data

    # Create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    # Verify links exist
    from sqlmodel import select

    links_before = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary_id
        )
    ).all()
    assert len(links_before) == 2

    # Delete the summary invoice
    response = client.delete(f"/invoices/summary/{summary_id}")
    assert response.status_code == 204

    # Verify links are also deleted
    links_after = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary_id
        )
    ).all()
    assert len(links_after) == 0


def test_delete_summary_invoice_preserves_original_invoices(
    client, sample_data, session
):
    """Test that deleting summary invoice doesn't delete original invoices."""
    data = sample_data

    # Create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    # Delete the summary invoice
    response = client.delete(f"/invoices/summary/{summary_id}")
    assert response.status_code == 204

    # Verify original invoices still exist
    invoice1 = session.get(Invoice, data["invoices"][0].id)
    invoice2 = session.get(Invoice, data["invoices"][1].id)
    assert invoice1 is not None
    assert invoice2 is not None


# =============================================================================
# ERROR CASES - DELETE SUMMARY INVOICE
# =============================================================================


def test_delete_summary_invoice_not_found(client):
    """Test deleting non-existent summary invoice."""
    response = client.delete("/invoices/summary/9999")

    assert response.status_code == 404
    error = response.json()
    assert "detail" in error
    assert any("not found" in str(detail).lower() for detail in error["detail"])


def test_delete_summary_invoice_invalid_id(client):
    """Test deleting summary invoice with invalid ID format."""
    response = client.delete("/invoices/summary/not_an_integer")

    assert response.status_code == 422  # Validation error
    error = response.json()
    assert "detail" in error


def test_delete_summary_invoice_already_deleted(client, sample_data):
    """Test deleting already deleted summary invoice."""
    data = sample_data

    # Create a summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    summary_id = create_response.json()["id"]

    # Delete it once
    response1 = client.delete(f"/invoices/summary/{summary_id}")
    assert response1.status_code == 204

    # Try to delete again
    response2 = client.delete(f"/invoices/summary/{summary_id}")
    assert response2.status_code == 404


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


def test_full_crud_workflow(client, sample_data):
    """Test complete CRUD workflow for summary invoices."""
    data = sample_data

    # 1. Create summary invoice
    payload = {
        "profile_id": data["profile"].id,
        "invoice_ids": [data["invoices"][0].id, data["invoices"][1].id],
    }
    create_response = client.post("/summary-invoices", json=payload)
    assert create_response.status_code == 201
    summary_id = create_response.json()["id"]

    # 2. Read single summary invoice
    get_response = client.get(f"/invoices/summary/{summary_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == summary_id

    # 3. Read list of summary invoices
    list_response = client.get("/summary-invoices")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    # 4. Delete summary invoice
    delete_response = client.delete(f"/invoices/summary/{summary_id}")
    assert delete_response.status_code == 204

    # 5. Verify deletion
    get_after_delete = client.get(f"/invoices/summary/{summary_id}")
    assert get_after_delete.status_code == 404

    list_after_delete = client.get("/summary-invoices")
    assert list_after_delete.status_code == 200
    assert len(list_after_delete.json()) == 0


def test_concurrent_operations(client, sample_data):
    """Test concurrent creation and reading of summary invoices."""
    data = sample_data

    # Create multiple summary invoices
    payloads = [
        {"profile_id": data["profile"].id, "invoice_ids": [data["invoices"][0].id]},
        {"profile_id": data["profile"].id, "invoice_ids": [data["invoices"][1].id]},
        {
            "profile_id": data["profile_no_tax"].id,
            "invoice_ids": [data["invoices"][2].id],
        },
    ]

    created_ids = []
    for payload in payloads:
        response = client.post("/summary-invoices", json=payload)
        assert response.status_code == 201
        created_ids.append(response.json()["id"])

    # Verify all exist
    list_response = client.get("/summary-invoices")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 3

    # Verify individual access
    for summary_id in created_ids:
        response = client.get(f"/invoices/summary/{summary_id}")
        assert response.status_code == 200
        assert response.json()["id"] == summary_id
