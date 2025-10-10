import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 🧩 Fixtures – Basis-Setup für alle Tests
# ---------------------------------------------------------------------------


@pytest.fixture
def base_profile():
    """Profil mit 19% MwSt"""
    resp = client.post(
        "/profiles/",
        json={
            "name": "Salon Berlin",
            "address": "Hauptstraße 1",
            "city": "Berlin",
            "include_tax": True,
            "default_tax_rate": 0.19,
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.fixture
def reduced_profile():
    """Profil mit 7% MwSt"""
    resp = client.post(
        "/profiles/",
        json={
            "name": "Kunsthandel",
            "address": "Museumsweg 2",
            "city": "Hamburg",
            "include_tax": True,
            "default_tax_rate": 0.07,
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.fixture
def taxfree_profile():
    """Profil ohne MwSt (§19 UStG)"""
    resp = client.post(
        "/profiles/",
        json={
            "name": "Kleinunternehmer",
            "address": "Freiweg 3",
            "city": "Leipzig",
            "include_tax": False,
            "default_tax_rate": 0.0,
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.fixture
def customer():
    resp = client.post("/customers/", json={"name": "Testkunde"})
    assert resp.status_code in (200, 201)
    return resp.json()


# ---------------------------------------------------------------------------


def test_happy_inherits_tax_from_profile(base_profile, customer):
    """Invoice übernimmt Steuerlogik vom Profil"""
    invoice = {
        "number": "25|500",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["include_tax"] is True
    assert round(data["tax_rate"], 2) == 0.19


def test_happy_overrides_tax_fields(taxfree_profile, customer):
    """Invoice kann include_tax und tax_rate überschreiben"""
    invoice = {
        "number": "25|501",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "include_tax": True,
        "tax_rate": 0.07,
        "invoice_items": [{"description": "Färben", "quantity": 1, "price": 50.0}],
        "total_amount": 50.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["include_tax"] is True
    assert round(data["tax_rate"], 2) == 0.07
    


def test_happy_taxfree_profile(taxfree_profile, customer):
    """Invoice übernimmt steuerfreie Einstellung"""
    invoice = {
        "number": "25|502",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "invoice_items": [{"description": "Steuerfrei", "quantity": 1, "price": 80.0}],
        "total_amount": 80.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["include_tax"] is False
    assert round(data["tax_rate"], 2) == 0.0


def test_happy_gross_amount(base_profile, customer):
    """Bruttobetrag bleibt gleich, MwSt enthalten"""
    invoice = {
        "number": "25|503",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "is_gross_amount": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 119.0}
        ],
        "total_amount": 119.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["is_gross_amount"] is True
    assert round(data["total_amount"], 2) == 119.00


def test_happy_net_amount(reduced_profile, customer):
    """Nettobetrag wird gespeichert, Steuer wird nur angezeigt (z. B. im PDF)"""
    invoice = {
        "number": "25|504",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": reduced_profile["id"],
        "include_tax": True,
        "is_gross_amount": False,  # Netto-Angabe
        "tax_rate": 0.07,
        "invoice_items": [
            {"description": "Kunstverkauf", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,  # Netto-Betrag, noch ohne Steuer
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["include_tax"] is True
    assert round(data["tax_rate"], 2) == 0.07
    assert round(data["total_amount"], 2) == 100.00  # Netto gespeichert

    # Optionale Logikprüfung (nicht in DB, nur konzeptionell)
    brutto_berechnet = data["total_amount"] * (1 + data["tax_rate"])
    assert round(brutto_berechnet, 2) == 107.00

def test_happy_gross_amount(base_profile, customer):
    """Bruttobetrag wird gespeichert, Netto wird aus total_amount abgeleitet"""
    invoice = {
        "number": "25|503",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "is_gross_amount": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 119.0}
        ],
        "total_amount": 119.0,  # Bruttobetrag
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    # Gespeicherte Daten
    assert data["include_tax"] is True
    assert data["is_gross_amount"] is True
    assert round(data["tax_rate"], 2) == 0.19
    assert round(data["total_amount"], 2) == 119.00  # Brutto gespeichert

    # Logisch abgeleitete Werte (nicht in DB, nur konzeptionell)
    netto = data["total_amount"] / (1 + data["tax_rate"])
    steuer = data["total_amount"] - netto

    assert round(netto, 2) == 100.00
    assert round(steuer, 2) == 19.00



def test_happy_rounding_and_sum_consistency(base_profile, customer):
    """Summe der Items ≈ total_amount (max 1 Cent Abweichung)"""
    invoice = {
        "number": "25|505",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Waschen", "quantity": 1, "price": 10.55},
            {"description": "Schneiden", "quantity": 1, "price": 23.45},
        ],
        "total_amount": 34.00,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    subtotal = sum(i["quantity"] * i["price"] for i in invoice["invoice_items"])
    assert abs(subtotal - data["total_amount"]) < 0.05

def test_happy_net_amount_with_tax_rate_zero(taxfree_profile, customer):
    """Nettobetrag + 0% MwSt = Gesamtbetrag (steuerfrei)"""
    invoice = {
        "number": "25|987",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "include_tax": False,
        "is_gross_amount": False,
        "tax_rate": 0.0,  
        "invoice_items": [{"description": "Steuerfrei", "quantity": 1, "price": 100.0}],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()
    assert data["include_tax"] is False
    assert round(data["tax_rate"], 2) == 0.0

def test_happy_taxfree_invoice_with_is_gross_amount_flag(taxfree_profile, customer):
    """is_gross_amount kann beliebig sein, wenn include_tax False"""
    invoice = {
        "number": "25|985",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "include_tax": False,
        "is_gross_amount": False,  # erlaubt, da keine Steuerpflicht
        "tax_rate": 0.0,
        "invoice_items": [{"description": "Steuerfrei", "quantity": 1, "price": 100.0}],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 201
    data = resp.json()

    assert data["include_tax"] is False
    assert data["is_gross_amount"] is False
    assert data["tax_rate"] == 0.0

