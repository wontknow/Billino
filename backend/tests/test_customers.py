import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool

from main import app
from database import get_session, init_db

# Einmalige Test-DB im Speicher (mit StaticPool für persistente Verbindung)
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,   # <--- hält dieselbe DB für alle Connections
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
        json={"name": "Anna Müller", "address": "Hauptstr. 1, 12345 Berlin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Anna Müller"
    assert data["address"] == "Hauptstr. 1, 12345 Berlin"


def test_create_customer_without_address(client):
    response = client.post("/customers", json={"name": "Peter Schmidt"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "Peter Schmidt"
    assert data["address"] is None



def test_list_customers(client):
    client.post("/customers", json={"name": "Peter Schmidt", "address": "Nebenstr. 2"})
    resp = client.get("/customers")
    assert resp.status_code == 200
    data = resp.json()
    assert any(c["name"] == "Peter Schmidt" for c in data)


def test_update_customer(client):
    # Erst anlegen
    resp = client.post("/customers", json={"name": "Max Mustermann", "address": "Altstr. 1"})
    cust = resp.json()

    # Update-Request
    resp2 = client.put(f"/customers/{cust['id']}", json={"name": "Maxi Mustermann", "address": "Neu Str. 99"})
    assert resp2.status_code == 200
    updated = resp2.json()
    assert updated["name"] == "Maxi Mustermann"
    assert updated["address"] == "Neu Str. 99"

    # Prüfen ob GET-Liste auch geupdatet ist
    resp3 = client.get("/customers")
    names = [c["name"] for c in resp3.json()]
    assert "Maxi Mustermann" in names


def test_delete_customer(client):
    # Erst anlegen
    resp = client.post("/customers", json={"name": "Lösch Mich", "address": "Testweg 5"})
    cust = resp.json()

    # Delete-Request
    resp2 = client.delete(f"/customers/{cust['id']}")
    assert resp2.status_code == 204
    assert resp2.content == b''

    # Prüfen, dass Kunde nicht mehr in Liste ist
    resp3 = client.get("/customers")
    ids = [c["id"] for c in resp3.json()]
    assert cust["id"] not in ids
