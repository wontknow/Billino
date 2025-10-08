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


def test_error_missing_profile(customer):
    """Fehler, wenn kein Profil angegeben"""
    invoice = {
        "number": "25|998",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Field required"


def test_error_missing_customer(base_profile):
    """Fehler, wenn kein Kunde angegeben"""
    invoice = {
        "number": "25|997",
        "date": "2025-10-05",
        "profile_id": base_profile["id"],
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Field required"


def test_invalid_tax_rate_negative(base_profile, customer):
    """Fehler bei ungültigem tax_rate"""
    invoice = {
        "number": "25|996",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": -0.05,  # Ungültig
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Value error, tax_rate must be between 0 and 1."


def test_invalid_tax_rate_too_high(base_profile, customer):
    """Fehler bei ungültigem tax_rate"""
    invoice = {
        "number": "25|995",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": 1.5,  # Ungültig
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Value error, tax_rate must be between 0 and 1."


def test_include_tax_true_without_tax_rate(base_profile, customer):
    """Fehler, wenn include_tax True aber kein tax_rate"""
    invoice = {
        "number": "25|994",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": None,  # Fehlend
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }
    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"] == "Value error, tax_rate must be provided if include_tax is True."
    )


def test_error_set_tax_rate_with_taxfree_profile(taxfree_profile, customer):
    """Fehler, wenn tax_rate bei steuerfreiem Profil gesetzt wird"""
    invoice = {
        "number": "25|993",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "include_tax": False,
        "tax_rate": 0.19,  # Ungültig
        "invoice_items": [{"description": "Steuerfrei", "quantity": 1, "price": 80.0}],
        "total_amount": 80.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Value error, tax_rate must be 0 if include_tax is False."


def test_negative_total_amount(base_profile, customer):
    """Fehler bei negativem total_amount"""
    invoice = {
        "number": "25|992",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": -100.0,  # Ungültig
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Value error, total_amount must be non-negative."


def test_is_gross_amount_without_include_tax(base_profile, customer):
    """Fehler, wenn is_gross_amount gesetzt aber include_tax fehlt"""
    invoice = {
        "number": "25|991",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "is_gross_amount": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "Value error, is_gross_amount can only be True if include_tax is True."
    )


def test_is_gross_amount_include_tax_false(base_profile, customer):
    """Fehler, wenn is_gross_amount True aber include_tax False"""
    invoice = {
        "number": "25|990",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": False,
        "is_gross_amount": True,  # Ungültig
        "tax_rate": 0.0,
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "Value error, is_gross_amount can only be True if include_tax is True."
    )


def test_is_gross_amount_without_tax_rate(base_profile, customer):
    """Fehler, wenn is_gross_amount True aber kein tax_rate"""
    invoice = {
        "number": "25|989",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "is_gross_amount": True,
        "tax_rate": None,  # Fehlend
        "invoice_items": [
            {"description": "Haarschnitt", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "tax_rate must be provided if is_gross_amount is True."
    )


def test_net_amount_without_tax_rate(reduced_profile, customer):
    """Fehler, wenn is_gross_amount False aber kein tax_rate"""
    invoice = {
        "number": "25|988",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": reduced_profile["id"],
        "include_tax": True,
        "is_gross_amount": False,
        "tax_rate": None,  # Fehlend
        "invoice_items": [
            {"description": "Kunstverkauf", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 107.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "tax_rate must be provided if is_gross_amount is False."
    )


def test_net_amount_with_tax_rate_zero(taxfree_profile, customer):
    """Fehler, wenn is_gross_amount False aber tax_rate 0"""
    invoice = {
        "number": "25|987",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": taxfree_profile["id"],
        "include_tax": False,
        "is_gross_amount": False,
        "tax_rate": 0.0,  # Ungültig
        "invoice_items": [{"description": "Steuerfrei", "quantity": 1, "price": 100.0}],
        "total_amount": 100.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "tax_rate must be greater than 0 if is_gross_amount is False."
    )


def test_net_amount_with_tax_rate_negative(reduced_profile, customer):
    """Fehler, wenn is_gross_amount False aber tax_rate negativ"""
    invoice = {
        "number": "25|986",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": reduced_profile["id"],
        "include_tax": True,
        "is_gross_amount": False,
        "tax_rate": -0.07,  # Ungültig
        "invoice_items": [
            {"description": "Kunstverkauf", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 107.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert data["detail"][0]["msg"] == "Value error, tax_rate must be between 0 and 1."


def test_net_amount_include_tax_false(reduced_profile, customer):
    """Fehler, wenn is_gross_amount False aber include_tax False"""
    invoice = {
        "number": "25|985",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": reduced_profile["id"],
        "include_tax": False,
        "is_gross_amount": False,  # Ungültig
        "tax_rate": 0.07,
        "invoice_items": [
            {"description": "Kunstverkauf", "quantity": 1, "price": 100.0}
        ],
        "total_amount": 107.0,
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "is_gross_amount can only be False if include_tax is True."
    )


def test_rounding_error_too_high(base_profile, customer):
    """Fehler, wenn Summe der Items > total_amount + 1 Cent"""
    invoice = {
        "number": "25|984",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Waschen", "quantity": 1, "price": 10.55},
            {"description": "Schneiden", "quantity": 1, "price": 23.45},
        ],
        "total_amount": 34.00,  # Korrekt wäre 34.00 + 0.01
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "Sum of invoice items exceeds total_amount by more than 0.01."
    )


def test_rounding_error_too_low(base_profile, customer):
    """Fehler, wenn Summe der Items < total_amount - 1 Cent"""
    invoice = {
        "number": "25|983",
        "date": "2025-10-05",
        "customer_id": customer["id"],
        "profile_id": base_profile["id"],
        "include_tax": True,
        "tax_rate": 0.19,
        "invoice_items": [
            {"description": "Waschen", "quantity": 1, "price": 10.55},
            {"description": "Schneiden", "quantity": 1, "price": 23.45},
        ],
        "total_amount": 34.00,  # Korrekt wäre 34.00 - 0.01
    }

    resp = client.post("/invoices/", json=invoice)
    assert resp.status_code == 422
    data = resp.json()
    assert (
        data["detail"][0]["msg"]
        == "Sum of invoice items is less than total_amount by more than 0.01."
    )
