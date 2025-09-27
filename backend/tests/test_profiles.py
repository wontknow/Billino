from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_profile():
    response = client.post(
        "/profiles/", json={"name": "Test Profile", "address": "123 Test Street"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Profile"
    assert response.json()["address"] == "123 Test Street"


def test_create_profile_with_optional_fields():
    response = client.post(
        "/profiles/",
        json={
            "name": "Full Profile",
            "address": "456 Full Street",
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


def test_get_profile():
    # Erstellt ein Profil zum Abrufen
    create_response = client.post(
        "/profiles/", json={"name": "Get Profile", "address": "789 Get Street"}
    )
    profile_id = create_response.json()["id"]

    response = client.get(f"/profiles/{profile_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["name"] == "Get Profile"
    assert data["address"] == "789 Get Street"


def test_get_profile_list():
    response = client.get("/profiles/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_profile():
    # Erstellt ein Profil zum Aktualisieren
    create_response = client.post(
        "/profiles/", json={"name": "Update Profile", "address": "123 Update Street"}
    )
    profile_id = create_response.json()["id"]

    response = client.put(
        f"/profiles/{profile_id}",
        json={"name": "Updated Profile", "address": "456 Updated Street"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile_id
    assert data["name"] == "Updated Profile"
    assert data["address"] == "456 Updated Street"


def test_delete_profile():
    # Erstellt ein Profil zum Löschen
    create_response = client.post(
        "/profiles/", json={"name": "Delete Profile", "address": "123 Delete Street"}
    )
    profile_id = create_response.json()["id"]

    response = client.delete(f"/profiles/{profile_id}")
    assert response.status_code == 204

    response = client.get(f"/profiles/{profile_id}")
    assert response.status_code == 404
