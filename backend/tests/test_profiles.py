from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_create_profile():
    response = client.post(
        "/profiles/",
        json={
            "name": "Test Profile",
            "address": "123 Test Street",
            "city": "Test City",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Profile"
    assert response.json()["address"] == "123 Test Street"
    assert response.json()["city"] == "Test City"


def test_create_profile_with_optional_fields():
    response = client.post(
        "/profiles/",
        json={
            "name": "Full Profile",
            "address": "456 Full Street",
            "city": "Full City",
            "bank_data": "DE89 3704 0044 0532 0130 00",
            "tax_number": "123/456/78901",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["bank_data"] == "DE89 3704 0044 0532 0130 00"
    assert data["tax_number"] == "123/456/78901"
    assert data["name"] == "Full Profile"
    assert data["address"] == "456 Full Street"
    assert data["city"] == "Full City"


def test_get_profile():
    # Erstellt ein Profil zum Abrufen
    create_response = client.post(
        "/profiles/",
        json={"name": "Get Profile", "address": "789 Get Street", "city": "Get City"},
    )
    profile_id = create_response.json()["id"]

    response = client.get(f"/profiles/{profile_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["name"] == "Get Profile"
    assert data["address"] == "789 Get Street"
    assert data["city"] == "Get City"


def test_get_profile_list():
    response = client.get("/profiles/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_profile():
    # Erstellt ein Profil zum Aktualisieren
    create_response = client.post(
        "/profiles/",
        json={
            "name": "Update Profile",
            "address": "123 Update Street",
            "city": "Update City",
        },
    )
    profile_id = create_response.json()["id"]

    response = client.put(
        f"/profiles/{profile_id}",
        json={
            "name": "Updated Profile",
            "address": "456 Updated Street",
            "city": "Updated City",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["name"] == "Updated Profile"
    assert data["address"] == "456 Updated Street"
    assert data["city"] == "Updated City"


def test_delete_profile():
    # Erstellt ein Profil zum Löschen
    create_response = client.post(
        "/profiles/",
        json={
            "name": "Delete Profile",
            "address": "123 Delete Street",
            "city": "Delete City",
        },
    )
    profile_id = create_response.json()["id"]

    response = client.delete(f"/profiles/{profile_id}")
    assert response.status_code == 204

    response = client.get(f"/profiles/{profile_id}")
    assert response.status_code == 404


def test_profile_tax_defaults():
    """Prüft, dass neue Steuerfelder in Profil standardmäßig korrekt gesetzt sind."""
    response = client.post(
        "/profiles/",
        json={"name": "Tax Profile", "address": "Steuerstraße 1", "city": "Tax City"},
    )
    assert response.status_code == 201
    data = response.json()
    # Default Werte prüfen
    assert data["include_tax"] is True
    assert data["default_tax_rate"] == 0.19
