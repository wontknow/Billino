import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from database import get_session, init_db
from main import app

# Einmalige Test-DB im Speicher (mit StaticPool für persistente Verbindung)
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # <--- hält dieselbe DB für alle Connections
    )
    init_db(engine)  # erstellt alle Tabellen aus models
    return engine


@pytest.fixture(scope="session")
def client(engine):
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


class TestPDFRoutes:
    """Test PDF CRUD endpoints"""

    def test_create_invoice_pdf(self, client, session):
        """Test creating and storing an invoice PDF"""
        # Create profile and customer first
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Test Profile",
                "address": "Test Address",
                "city": "Test City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post(
            "/customers/",
            json={
                "name": "Test Customer",
                "address": "Customer Address",
                "city": "Customer City",
            },
        )
        customer_id = customer_resp.json()["id"]

        # Create invoice
        invoice_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer_id,
                "profile_id": profile_id,
                "total_amount": 100.00,
                "invoice_items": [
                    {"description": "Test Service", "quantity": 1, "price": 100.00}
                ],
            },
        )
        invoice_id = invoice_resp.json()["id"]

        # Create PDF
        pdf_resp = client.post(f"/pdfs/invoices/{invoice_id}")

        assert pdf_resp.status_code == 201
        pdf_data = pdf_resp.json()
        assert "id" in pdf_data
        assert pdf_data["invoice_id"] == invoice_id
        assert pdf_data["type"] == "invoice"
        assert len(pdf_data["content"]) > 0  # Base64 encoded PDF

    def test_create_summary_invoice_pdf(self, client, session):
        """Test creating and storing a summary invoice PDF"""
        # Create profile and customer
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Summary Profile",
                "address": "Summary Address",
                "city": "Summary City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post("/customers/", json={"name": "Summary Customer"})
        customer_id = customer_resp.json()["id"]

        # Create invoices
        invoice_ids = []
        for i in range(2):
            invoice_resp = client.post(
                "/invoices/",
                json={
                    "date": "2025-10-21",
                    "customer_id": customer_id,
                    "profile_id": profile_id,
                    "total_amount": 50.00,
                    "invoice_items": [
                        {"description": f"Service {i+1}", "quantity": 1, "price": 50.00}
                    ],
                },
            )
            invoice_ids.append(invoice_resp.json()["id"])

        # Create summary invoice
        summary_resp = client.post(
            "/summary-invoices/",
            json={
                "profile_id": profile_id,
                "invoice_ids": invoice_ids,
                "range_text": "Test Range",
                "date": "2025-10-21",
            },
        )
        summary_id = summary_resp.json()["id"]

        # Create PDF for summary invoice (with recipient name)
        pdf_resp = client.post(
            f"/pdfs/summary-invoices/{summary_id}", 
            json={"recipient_name": "Seniorenresidenz Sonnenschein"}
        )

        assert pdf_resp.status_code == 201
        pdf_data = pdf_resp.json()
        assert "id" in pdf_data
        assert pdf_data["summary_invoice_id"] == summary_id
        assert pdf_data["type"] == "summary_invoice"
        assert len(pdf_data["content"]) > 0  # Base64 encoded PDF

    def test_create_summary_invoice_pdf_without_recipient(self, client, session):
        """Test creating PDF for summary invoice without recipient name (fallback to customer names)"""
        # Create profile and customers first
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Fallback Profile",
                "address": "Fallback Address", 
                "city": "Fallback City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer1_resp = client.post("/customers/", json={"name": "Hans Müller"})
        customer1_id = customer1_resp.json()["id"]
        
        customer2_resp = client.post("/customers/", json={"name": "Maria Schmidt"})
        customer2_id = customer2_resp.json()["id"]

        # Create invoices for both customers
        invoice1_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer1_id,
                "profile_id": profile_id,
                "total_amount": 50.00,
                "invoice_items": [
                    {"description": "Service 1", "quantity": 1, "price": 50.00}
                ],
            },
        )
        invoice1_id = invoice1_resp.json()["id"]

        invoice2_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer2_id,
                "profile_id": profile_id,
                "total_amount": 75.00,
                "invoice_items": [
                    {"description": "Service 2", "quantity": 1, "price": 75.00}
                ],
            },
        )
        invoice2_id = invoice2_resp.json()["id"]

        # Create summary invoice
        summary_resp = client.post(
            "/summary-invoices/",
            json={
                "invoice_ids": [invoice1_id, invoice2_id],
                "profile_id": profile_id,
                "range_text": "Fallback Test Range",
                "date": "2025-10-21",
            },
        )
        summary_id = summary_resp.json()["id"]

        # Create PDF for summary invoice WITHOUT recipient_name (should fallback to customer names)
        pdf_resp = client.post(f"/pdfs/summary-invoices/{summary_id}")
        
        assert pdf_resp.status_code == 201
        pdf_data = pdf_resp.json()
        assert "id" in pdf_data
        assert pdf_data["summary_invoice_id"] == summary_id
        assert pdf_data["type"] == "summary_invoice"
        assert len(pdf_data["content"]) > 0  # Base64 encoded PDF

    def test_get_pdf_list(self, client, session):
        """Test getting list of all PDFs"""
        resp = client.get("/pdfs/")

        assert resp.status_code == 200
        pdfs = resp.json()
        assert isinstance(pdfs, list)
        # Should contain PDFs from previous tests

    def test_get_pdf_by_id(self, client, session):
        """Test getting a specific PDF by ID"""
        # First create a PDF
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Get PDF Profile",
                "address": "Get PDF Address",
                "city": "Get PDF City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post("/customers/", json={"name": "Get PDF Customer"})
        customer_id = customer_resp.json()["id"]

        invoice_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer_id,
                "profile_id": profile_id,
                "total_amount": 75.00,
                "invoice_items": [
                    {"description": "Get Test Service", "quantity": 1, "price": 75.00}
                ],
            },
        )
        invoice_id = invoice_resp.json()["id"]

        pdf_resp = client.post(f"/pdfs/invoices/{invoice_id}")
        pdf_id = pdf_resp.json()["id"]

        # Get the PDF
        get_resp = client.get(f"/pdfs/{pdf_id}")

        assert get_resp.status_code == 200
        pdf_data = get_resp.json()
        assert pdf_data["id"] == pdf_id
        assert pdf_data["invoice_id"] == invoice_id
        assert len(pdf_data["content"]) > 0

    def test_delete_pdf(self, client, session):
        """Test deleting a PDF"""
        # First create a PDF
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Delete PDF Profile",
                "address": "Delete PDF Address",
                "city": "Delete PDF City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post("/customers/", json={"name": "Delete PDF Customer"})
        customer_id = customer_resp.json()["id"]

        invoice_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer_id,
                "profile_id": profile_id,
                "total_amount": 25.00,
                "invoice_items": [
                    {
                        "description": "Delete Test Service",
                        "quantity": 1,
                        "price": 25.00,
                    }
                ],
            },
        )
        invoice_id = invoice_resp.json()["id"]

        pdf_resp = client.post(f"/pdfs/invoices/{invoice_id}")
        pdf_id = pdf_resp.json()["id"]

        # Delete the PDF
        delete_resp = client.delete(f"/pdfs/{pdf_id}")

        assert delete_resp.status_code == 204

        # Verify it's gone
        get_resp = client.get(f"/pdfs/{pdf_id}")
        assert get_resp.status_code == 404

    def test_pdf_not_found(self, client, session):
        """Test getting non-existent PDF returns 404"""
        resp = client.get("/pdfs/999999")
        assert resp.status_code == 404

    def test_invoice_not_found_for_pdf_creation(self, client, session):
        """Test creating PDF for non-existent invoice returns 404"""
        resp = client.post("/pdfs/invoices/999999")
        assert resp.status_code == 404

    def test_summary_invoice_not_found_for_pdf_creation(self, client, session):
        """Test creating PDF for non-existent summary invoice returns 404"""
        resp = client.post("/pdfs/summary-invoices/999999", json={"recipient_name": "Test Recipient"})
        assert resp.status_code == 404

    def test_pdf_already_exists(self, client, session):
        """Test creating a PDF for an invoice that already has a stored PDF returns 400"""
        # Create profile and customer first
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Existing PDF Profile",
                "address": "Existing PDF Address",
                "city": "Existing PDF City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post(
            "/customers/",
            json={
                "name": "Existing PDF Customer",
                "address": "Customer Address",
                "city": "Customer City",
            },
        )
        customer_id = customer_resp.json()["id"]

        # Create invoice
        invoice_resp = client.post(
            "/invoices/",
            json={
                "date": "2025-10-21",
                "customer_id": customer_id,
                "profile_id": profile_id,
                "total_amount": 100.00,
                "invoice_items": [
                    {"description": "Test Service", "quantity": 1, "price": 100.00}
                ],
            },
        )
        invoice_id = invoice_resp.json()["id"]

        # Create PDF first time
        pdf_resp1 = client.post(f"/pdfs/invoices/{invoice_id}")
        assert pdf_resp1.status_code == 201

        # Attempt to create PDF second time
        pdf_resp2 = client.post(f"/pdfs/invoices/{invoice_id}")
        assert pdf_resp2.status_code == 400

    def test_pdf_already_exists_summary_invoice(self, client, session):
        """Test creating a PDF for a summary invoice that already has a stored PDF returns 400"""
        # Create profile and customer
        profile_resp = client.post(
            "/profiles/",
            json={
                "name": "Existing Summary PDF Profile",
                "address": "Existing Summary PDF Address",
                "city": "Existing Summary PDF City",
            },
        )
        profile_id = profile_resp.json()["id"]

        customer_resp = client.post(
            "/customers/", json={"name": "Existing Summary PDF Customer"}
        )
        customer_id = customer_resp.json()["id"]

        # Create invoices
        invoice_ids = []
        for i in range(2):
            invoice_resp = client.post(
                "/invoices/",
                json={
                    "date": "2025-10-21",
                    "customer_id": customer_id,
                    "profile_id": profile_id,
                    "total_amount": 50.00,
                    "invoice_items": [
                        {"description": f"Service {i+1}", "quantity": 1, "price": 50.00}
                    ],
                },
            )
            invoice_ids.append(invoice_resp.json()["id"])

        # Create summary invoice
        summary_resp = client.post(
            "/summary-invoices/",
            json={
                "profile_id": profile_id,
                "invoice_ids": invoice_ids,
                "range_text": "Test Range",
                "date": "2025-10-21",
            },
        )
        summary_id = summary_resp.json()["id"]

        # Create PDF for summary invoice first time
        pdf_resp1 = client.post(
            f"/pdfs/summary-invoices/{summary_id}", json={"recipient_name": "Test Recipient"}
        )
        assert pdf_resp1.status_code == 201

        # Attempt to create PDF second time
        pdf_resp2 = client.post(
            f"/pdfs/summary-invoices/{summary_id}", json={"recipient_name": "Test Recipient"}
        )
        assert pdf_resp2.status_code == 400
        assert (
            pdf_resp2.json()["detail"] == "PDF for this summary invoice already exists"
        )
