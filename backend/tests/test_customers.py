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


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    """FastAPI TestClient mit Session-Override."""

    def get_session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as c:
        yield c


def test_models_registered(engine):
    """Prüfen, ob Customer-Tabelle registriert ist."""
    assert "customer" in SQLModel.metadata.tables


def test_create_customer_with_address(client):
    response = client.post(
        "/customers",
        json={
            "name": "Anna Müller",
            "address": "Hauptstr. 1, 12345 Berlin",
            "city": "Berlin",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Anna Müller"
    assert data["address"] == "Hauptstr. 1, 12345 Berlin"
    assert data["city"] == "Berlin"


def test_create_customer_without_address(client):
    response = client.post(
        "/customers", json={"name": "Peter Schmidt", "city": "München"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Peter Schmidt"
    assert data["address"] is None


def test_create_customer_without_city(client):
    response = client.post(
        "/customers", json={"name": "Peter Schmidt", "address": "Nebenstr. 2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Peter Schmidt"
    assert data["address"] == "Nebenstr. 2"
    assert data["city"] is None


def test_list_customers(client):
    client.post("/customers", json={"name": "Peter Schmidt", "address": "Nebenstr. 2"})
    resp = client.get("/customers")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["name"] == "Peter Schmidt" for c in data)


def test_update_customer(client):
    # Erst anlegen
    resp = client.post(
        "/customers",
        json={"name": "Max Mustermann", "address": "Altstr. 1", "city": "Old City"},
    )
    cust = resp.json()

    # Update-Request
    resp2 = client.put(
        f"/customers/{cust['id']}",
        json={"name": "Maxi Mustermann", "address": "Neu Str. 99", "city": "Old City"},
    )
    assert resp2.status_code == 200
    updated = resp2.json()
    assert updated["name"] == "Maxi Mustermann"
    assert updated["address"] == "Neu Str. 99"
    assert updated["city"] == "Old City"

    # Prüfen ob GET-Liste auch geupdatet ist
    resp3 = client.get("/customers")
    names = [c["name"] for c in resp3.json()]
    assert "Maxi Mustermann" in names


def test_delete_customer(client):
    # Erst anlegen
    resp = client.post(
        "/customers",
        json={"name": "Lösch Mich", "address": "Testweg 5", "city": "Test City"},
    )
    cust = resp.json()

    # Delete-Request
    resp2 = client.delete(f"/customers/{cust['id']}")
    assert resp2.status_code == 204
    assert resp2.content == b""

    # Prüfen, dass Kunde nicht mehr in Liste ist
    resp3 = client.get("/customers")
    ids = [c["id"] for c in resp3.json()]
    assert cust["id"] not in ids


# ===== Search Endpoint Tests =====


def test_search_customers_happy_path(client):
    """Test: Erfolgreiche Suche mit Treffern"""
    # Erstelle Test-Kunden
    client.post("/customers", json={"name": "Max Mustermann GmbH", "city": "Berlin"})
    client.post("/customers", json={"name": "Maxi Media AG", "city": "München"})
    client.post("/customers", json={"name": "Peter Schmidt", "city": "Hamburg"})

    # Suche nach "max" (case-insensitive)
    resp = client.get("/customers/search?q=max")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [c["name"] for c in data]
    assert "Max Mustermann GmbH" in names
    assert "Maxi Media AG" in names
    assert "Peter Schmidt" not in names


def test_search_customers_no_results(client):
    """Test: Suche ohne Treffer"""
    client.post("/customers", json={"name": "Anna Schmidt", "city": "Berlin"})

    resp = client.get("/customers/search?q=xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_search_customers_query_too_short(client):
    """Test: Query < 2 Zeichen → 422 Validation Error"""
    resp = client.get("/customers/search?q=a")
    assert resp.status_code == 422
    error = resp.json()
    assert "detail" in error


def test_search_customers_special_characters(client):
    """Test: Sonderzeichen in Query (SQL-Injection-Schutz)"""
    # Erstelle Test-Kunde mit Sonderzeichen
    client.post("/customers", json={"name": "Müller & Co. KG", "city": "Berlin"})
    client.post("/customers", json={"name": "50% Rabatt GmbH", "city": "München"})

    # Suche mit Prozentzeichen (SQL LIKE Wildcard)
    resp = client.get("/customers/search?q=50%25")  # URL-encoded %
    assert resp.status_code == 200
    data = resp.json()
    # Sollte nur "50% Rabatt GmbH" finden, nicht alle
    assert any(c["name"] == "50% Rabatt GmbH" for c in data)

    # Suche mit Unterstrich
    resp2 = client.get("/customers/search?q=müller")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert any(c["name"] == "Müller & Co. KG" for c in data2)


def test_search_customers_limit_parameter(client):
    """Test: Limit-Parameter funktioniert"""
    # Erstelle viele Test-Kunden
    for i in range(15):
        client.post("/customers", json={"name": f"Test Customer {i}", "city": "Berlin"})

    # Standard-Limit (10)
    resp = client.get("/customers/search?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10

    # Custom Limit (5)
    resp2 = client.get("/customers/search?q=test&limit=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 5

    # Max Limit (50)
    resp3 = client.get("/customers/search?q=test&limit=50")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3) >= 15  # Mindestens die 15 neu erstellten

    # Ungültiges Limit (> 50)
    resp4 = client.get("/customers/search?q=test&limit=100")
    assert resp4.status_code == 422
