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


# ===== Search Endpoint Tests =====


def test_search_profiles_happy_path():
    """Test: Erfolgreiche Suche mit Treffern"""
    # Erstelle Test-Profile
    client.post(
        "/profiles/",
        json={"name": "Max Mustermann", "address": "Str. 1", "city": "Berlin"},
    )
    client.post(
        "/profiles/",
        json={"name": "Maxi Design Studio", "address": "Str. 2", "city": "München"},
    )
    client.post(
        "/profiles/",
        json={"name": "Peter Schmidt", "address": "Str. 3", "city": "Hamburg"},
    )

    # Suche nach "max" (case-insensitive)
    resp = client.get("/profiles/search?q=max")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    names = [p["name"] for p in data]
    assert "Max Mustermann" in names
    assert "Maxi Design Studio" in names
    assert "Peter Schmidt" not in names


def test_search_profiles_no_results():
    """Test: Suche ohne Treffer"""
    client.post(
        "/profiles/",
        json={"name": "Anna Schmidt", "address": "Str. 1", "city": "Berlin"},
    )

    resp = client.get("/profiles/search?q=xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 0


def test_search_profiles_query_too_short():
    """Test: Query < 2 Zeichen → 422 Validation Error"""
    resp = client.get("/profiles/search?q=a")
    assert resp.status_code == 422
    error = resp.json()
    assert "detail" in error


def test_search_profiles_special_characters():
    """Test: Sonderzeichen in Query (SQL-Injection-Schutz)"""
    # Erstelle Test-Profile mit Sonderzeichen
    client.post(
        "/profiles/",
        json={"name": "Müller & Söhne", "address": "Str. 1", "city": "Berlin"},
    )
    client.post(
        "/profiles/",
        json={"name": "100% Design", "address": "Str. 2", "city": "München"},
    )

    # Suche mit Prozentzeichen (SQL LIKE Wildcard)
    resp = client.get("/profiles/search?q=100%25")  # URL-encoded %
    assert resp.status_code == 200
    data = resp.json()
    # Sollte "100% Design" finden
    assert any(p["name"] == "100% Design" for p in data)

    # Suche mit Umlauten
    resp2 = client.get("/profiles/search?q=müller")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert any(p["name"] == "Müller & Söhne" for p in data2)


def test_search_profiles_limit_parameter():
    """Test: Limit-Parameter funktioniert"""
    # Erstelle viele Test-Profile
    for i in range(15):
        client.post(
            "/profiles/",
            json={"name": f"Test Profile {i}", "address": "Str. 1", "city": "Berlin"},
        )

    # Standard-Limit (10)
    resp = client.get("/profiles/search?q=test")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10

    # Custom Limit (5)
    resp2 = client.get("/profiles/search?q=test&limit=5")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2) == 5

    # Max Limit (50)
    resp3 = client.get("/profiles/search?q=test&limit=50")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3) >= 15  # Mindestens die 15 neu erstellten

    # Ungültiges Limit (> 50)
    resp4 = client.get("/profiles/search?q=test&limit=100")
    assert resp4.status_code == 422
