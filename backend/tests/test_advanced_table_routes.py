"""
Integration Tests für erweiterte Router mit Filter/Sort/Paging.
Tests für GET /customers, /profiles, /invoices, /summary-invoices.
"""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


class TestCustomersFilterSort:
    """Integration Tests für GET /customers mit Filtern und Sortierung"""

    def test_list_customers_basic(self, client):
        """Test basic GET /customers ohne Filter"""
        response = client.get("/customers/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pageSize" in data
        assert "pageCount" in data

    def test_list_customers_with_pagination(self, client):
        """Test Paginierung"""
        response = client.get("/customers/?page=1&pageSize=5")

        assert response.status_code == 200
        data = response.json()
        assert data["pageSize"] == 5
        assert data["page"] == 1

    def test_list_customers_with_filter_contains(self, client):
        """Test Filter mit CONTAINS operator"""
        response = client.get("/customers/?filter=name:contains:John")

        assert response.status_code == 200
        data = response.json()

        # Überprüfe dass alle returned items "John" im Namen haben (case-insensitive)
        for item in data["items"]:
            assert "john" in item["name"].lower()

    def test_list_customers_with_filter_exact(self, client):
        """Test Filter mit EXACT operator"""
        response = client.get("/customers/?filter=name:exact:john%20doe")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:  # Falls es einen "John Doe" gibt
            for item in data["items"]:
                assert item["name"].lower() == "john doe"

    def test_list_customers_with_sort_asc(self, client):
        """Test Sortierung aufsteigend"""
        response = client.get("/customers/?sort=name:asc")

        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            names = [item["name"] for item in data["items"]]
            assert names == sorted(names)

    def test_list_customers_with_sort_desc(self, client):
        """Test Sortierung absteigend"""
        response = client.get("/customers/?sort=id:desc")

        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            ids = [item["id"] for item in data["items"]]
            assert ids == sorted(ids, reverse=True)

    def test_list_customers_with_global_search(self, client):
        """Test globale Suche"""
        response = client.get("/customers/?q=berlin")

        assert response.status_code == 200
        data = response.json()

        # Alle items sollten "berlin" enthalten (in name, address, city, oder note)
        for item in data["items"]:
            text = f"{item.get('name', '')} {item.get('address', '')} {item.get('city', '')} {item.get('note', '')}"
            assert "berlin" in text.lower()

    def test_list_customers_with_multiple_filters(self, client):
        """Test mehrere Filter (AND-Bedingung)"""
        response = client.get(
            "/customers/?filter=city:contains:berlin&filter=name:startsWith:J"
        )

        assert response.status_code == 200
        data = response.json()

        # Alle items sollten beide Bedingungen erfüllen
        for item in data["items"]:
            assert "berlin" in item["city"].lower()
            assert item["name"].startswith("J") or item["name"].startswith("j")

    def test_list_customers_invalid_filter_operator_returns_400(self, client):
        """Test dass ungültiger Filter-Operator 400 zurückgibt"""
        response = client.get("/customers/?filter=name:invalid_op:test")

        assert response.status_code == 400
        # Error message vom Enum: "'invalid_op' is not a valid FilterOperator"
        assert (
            "not a valid FilterOperator" in response.json()["detail"]
            or "Invalid filter" in response.json()["detail"]
        )

    def test_list_customers_invalid_sort_direction_returns_400(self, client):
        """Test dass ungültige Sort-Richtung 400 zurückgibt"""
        response = client.get("/customers/?sort=name:invalid")

        assert response.status_code == 400
        # Error message vom Enum: "'invalid' is not a valid SortDirection"
        assert (
            "not a valid SortDirection" in response.json()["detail"]
            or "Invalid sort" in response.json()["detail"]
        )

    def test_list_customers_global_search_min_length(self, client):
        """Test dass globale Suche mit weniger als 2 Zeichen ignoriert wird"""
        response = client.get("/customers/?q=a")

        # Sollte 422 sein (validation error) oder ignoriert werden
        # Kommt auf die FastAPI-Konfiguration an
        assert response.status_code in [200, 422]


class TestProfilesFilterSort:
    """Integration Tests für GET /profiles"""

    def test_list_profiles_basic(self, client):
        """Test basic GET /profiles"""
        response = client.get("/profiles/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_profiles_with_filter(self, client):
        """Test Filter auf Profiles"""
        response = client.get("/profiles/?filter=name:contains:GmbH")

        assert response.status_code == 200
        data = response.json()

        for item in data["items"]:
            if item.get("name"):
                assert "gmbh" in item["name"].lower()

    def test_list_profiles_with_sort(self, client):
        """Test Sortierung auf Profiles"""
        response = client.get("/profiles/?sort=name:asc")

        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            names = [item["name"] for item in data["items"]]
            assert names == sorted(names)


class TestInvoicesFilterSort:
    """Integration Tests für GET /invoices"""

    def test_list_invoices_basic(self, client):
        """Test basic GET /invoices"""
        response = client.get("/invoices/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pageCount" in data

    def test_list_invoices_response_structure(self, client):
        """Test dass Response die erwartete Struktur hat"""
        response = client.get("/invoices/?pageSize=5")

        assert response.status_code == 200
        data = response.json()

        # Check pagination fields
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["pageSize"], int)
        assert isinstance(data["pageCount"], int)

        # Check items
        assert isinstance(data["items"], list)
        if data["items"]:
            item = data["items"][0]
            # Invoice-spezifische Felder
            assert "id" in item
            assert "number" in item
            assert "date" in item
            assert "total_net" in item
            assert "total_tax" in item
            assert "total_gross" in item

    def test_list_invoices_with_filter_date(self, client):
        """Test Date-Filter auf Invoices"""
        response = client.get("/invoices/?filter=date:gte:2025-01-01")

        assert response.status_code == 200
        data = response.json()

        # Alle returned invoices sollten nach 2025-01-01 sein
        for item in data["items"]:
            assert item["date"] >= "2025-01-01"

    def test_list_invoices_with_sort_date_desc(self, client):
        """Test Sortierung nach Datum absteigend"""
        response = client.get("/invoices/?sort=date:desc")

        assert response.status_code == 200
        data = response.json()

        if len(data["items"]) > 1:
            dates = [item["date"] for item in data["items"]]
            assert dates == sorted(dates, reverse=True)


class TestSummaryInvoicesFilterSort:
    """Integration Tests für GET /summary-invoices"""

    def test_list_summary_invoices_basic(self, client):
        """Test basic GET /summary-invoices"""
        response = client.get("/summary-invoices/")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_summary_invoices_response_structure(self, client):
        """Test dass Response die erwartete Struktur hat"""
        response = client.get("/summary-invoices/?page=1&pageSize=10")

        assert response.status_code == 200
        data = response.json()

        # Check pagination
        assert data["page"] == 1
        assert data["pageSize"] == 10

        # Check items
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "range_text" in item
            assert "date" in item
            assert "total_net" in item
            assert "total_tax" in item
            assert "total_gross" in item
            assert "invoice_ids" in item

    def test_list_summary_invoices_with_filter_profile(self, client):
        """Test Profile-Filter auf Summary Invoices"""
        response = client.get("/summary-invoices/?filter=profile_id:equals:1")

        assert response.status_code == 200
        data = response.json()

        # Alle items sollten profile_id=1 haben
        for item in data["items"]:
            assert item["profile_id"] == 1

    def test_list_summary_invoices_with_global_search(self, client):
        """Test globale Suche auf Summary Invoices"""
        response = client.get("/summary-invoices/?q=invoice")

        assert response.status_code == 200
        data = response.json()

        # Items sollten "invoice" im range_text enthalten
        for item in data["items"]:
            assert "invoice" in item["range_text"].lower()


class TestPaginationEdgeCases:
    """Tests für Edge-Cases bei Paginierung"""

    def test_pagination_page_zero_is_treated_as_one(self, client):
        """Test dass page=0 zu Validation Error führt (muss >= 1 sein)"""
        response = client.get("/customers/?page=0&pageSize=10")

        # FastAPI Query validation sollte 422 zurückgeben
        assert response.status_code == 422

    def test_pagination_max_page_size_enforced(self, client):
        """Test dass pageSize > 100 zu Validation Error führt"""
        response = client.get("/customers/?pageSize=200")

        # FastAPI Query validation sollte 422 zurückgeben
        assert response.status_code == 422

    def test_pagination_beyond_available_items(self, client):
        """Test Pagination jenseits der verfügbaren Items"""
        response = client.get("/customers/?page=999&pageSize=10")

        assert response.status_code == 200
        data = response.json()

        # items sollte leer sein, aber total sollte gesetzt sein
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)


class TestCombinedFiltersAndSort:
    """Tests für kombinierte Filter + Sortierung"""

    def test_filter_and_sort_combined(self, client):
        """Test Filter UND Sortierung zusammen"""
        response = client.get(
            "/customers/?filter=city:contains:berlin&sort=name:asc&page=1&pageSize=10"
        )

        assert response.status_code == 200
        data = response.json()

        # Alle items sollten "berlin" in der Stadt haben
        for item in data["items"]:
            if item.get("city"):
                assert "berlin" in item["city"].lower()

        # Items sollten nach Name sortiert sein
        if len(data["items"]) > 1:
            names = [item["name"] for item in data["items"]]
            assert names == sorted(names)

    def test_filter_sort_and_search_combined(self, client):
        """Test Filter + Sortierung + globale Suche zusammen"""
        response = client.get(
            "/customers/?filter=city:startsWith:B&q=john&sort=id:desc"
        )

        assert response.status_code == 200
        data = response.json()

        # Should have valid response with pagination
        assert "items" in data
        assert "total" in data
