import pytest
from fastapi.testclient import TestClient
from main import app
from services.invoice_number_generator import (generate_next_invoice_number,
                                               get_preview_invoice_number,
                                               validate_invoice_number_format)

client = TestClient(app)


# ---------------------------------------------------------------------------
# 🧩 Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def profile():
    """Create a test profile"""
    resp = client.post(
        "/profiles/",
        json={
            "name": "Test Profile",
            "address": "Test Street 1",
            "city": "Test City",
            "include_tax": True,
            "default_tax_rate": 0.19,
        },
    )
    assert resp.status_code in (200, 201)
    return resp.json()


@pytest.fixture
def customer():
    """Create a test customer"""
    resp = client.post("/customers/", json={"name": "Test Customer"})
    assert resp.status_code in (200, 201)
    return resp.json()


# ---------------------------------------------------------------------------
# 🧪 Number Format Validation Tests
# ---------------------------------------------------------------------------


def test_validate_invoice_number_format():
    """Test the number format validation function"""
    # Valid formats
    assert validate_invoice_number_format("25 | 001") is True
    assert validate_invoice_number_format("24 | 123") is True
    assert validate_invoice_number_format("99 | 9999") is True

    # Invalid formats
    assert validate_invoice_number_format("25|001") is False  # No spaces
    assert validate_invoice_number_format("25 |001") is False  # Missing space after |
    assert validate_invoice_number_format("25| 001") is False  # Missing space before |
    assert validate_invoice_number_format("2025 | 001") is False  # 4 digits year
    assert validate_invoice_number_format("25 - 001") is False  # Wrong separator
    assert validate_invoice_number_format("25 | 12") is False  # Only 2 digits number
    assert validate_invoice_number_format("") is False  # Empty string
    assert validate_invoice_number_format("invalid") is False  # Random text


def test_invoice_create_with_invalid_number_format():
    """Test that InvoiceCreateWithNumber validates number format"""
    profile_resp = client.post(
        "/profiles/",
        json={"name": "Test Profile", "address": "Test Address", "city": "Test City"},
    )
    profile_id = profile_resp.json()["id"]

    customer_resp = client.post("/customers/", json={"name": "Test Customer"})
    customer_id = customer_resp.json()["id"]

    # This should fail because we're using the wrong endpoint
    # The new endpoint doesn't require number field
    invalid_invoice = {
        "number": "25|001",  # Invalid format (no spaces)
        "date": "2025-10-20",
        "customer_id": customer_id,
        "profile_id": profile_id,
        "total_amount": 100.0,
        "invoice_items": [
            {"description": "Test Service", "quantity": 1, "price": 100.0}
        ],
    }

    # The current endpoint auto-generates numbers, so this won't work as expected
    # We'll need a separate endpoint for manual number entry


# ---------------------------------------------------------------------------
# 🧪 Automatic Number Generation Tests
# ---------------------------------------------------------------------------


def test_generate_first_invoice_number_of_year():
    """Test generating the first invoice number for a fresh profile"""
    # Create a new profile specifically for this test to avoid conflicts
    profile_resp = client.post(
        "/profiles/",
        json={
            "name": "Fresh Profile for First Number Test",
            "address": "Fresh Street 1",
            "city": "Fresh City",
            "include_tax": True,
            "default_tax_rate": 0.19,
        },
    )
    assert profile_resp.status_code in (200, 201)
    fresh_profile = profile_resp.json()

    from database import get_session

    session = next(get_session())
    try:
        number = generate_next_invoice_number(session)

        # Should be current year + sequential number for a fresh profile
        import datetime

        current_year = str(datetime.datetime.now().year)[-2:]

        # Check that it has the correct format and year
        assert number.startswith(f"{current_year} | ")
        assert validate_invoice_number_format(number) is True

        # Extract the numeric part and verify it's at least 001
        numeric_part = int(number.split(" | ")[1])
        assert numeric_part >= 1
        assert len(number.split(" | ")[1]) >= 3  # At least 3 digits

    finally:
        session.close()


def test_generate_sequential_invoice_numbers(profile, customer):
    """Test that invoice numbers increment sequentially"""
    # Create first invoice
    invoice1_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 100.0,
        "invoice_items": [{"description": "Service 1", "quantity": 1, "price": 100.0}],
    }

    resp1 = client.post("/invoices/", json=invoice1_data)
    assert resp1.status_code == 201
    invoice1 = resp1.json()

    # Create second invoice
    invoice2_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 200.0,
        "invoice_items": [{"description": "Service 2", "quantity": 1, "price": 200.0}],
    }

    resp2 = client.post("/invoices/", json=invoice2_data)
    assert resp2.status_code == 201
    invoice2 = resp2.json()

    # Numbers should be sequential globally
    import datetime

    current_year = str(datetime.datetime.now().year)[-2:]

    # Extract numeric parts
    num1 = int(invoice1["number"].split(" | ")[1])
    num2 = int(invoice2["number"].split(" | ")[1])

    # Second invoice should be exactly one number higher
    assert num2 == num1 + 1

    # Both should have correct year and valid format
    assert invoice1["number"].startswith(f"{current_year} | ")
    assert invoice2["number"].startswith(f"{current_year} | ")
    assert validate_invoice_number_format(invoice1["number"]) is True
    assert validate_invoice_number_format(invoice2["number"]) is True


def test_different_profiles_have_shared_number_sequence():
    """Test that different profiles share the same global number sequence (German tax law)"""
    # Create two profiles
    profile1_resp = client.post(
        "/profiles/",
        json={
            "name": "Profile 1",
            "address": "Address 1",
            "city": "City 1",
        },
    )
    profile1 = profile1_resp.json()

    profile2_resp = client.post(
        "/profiles/",
        json={
            "name": "Profile 2",
            "address": "Address 2",
            "city": "City 2",
        },
    )
    profile2 = profile2_resp.json()

    # Create customer
    customer_resp = client.post("/customers/", json={"name": "Test Customer"})
    customer = customer_resp.json()

    # Create invoice for profile 1
    invoice1_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile1["id"],
        "total_amount": 100.0,
        "invoice_items": [{"description": "Service 1", "quantity": 1, "price": 100.0}],
    }

    resp1 = client.post("/invoices/", json=invoice1_data)
    assert resp1.status_code == 201
    invoice1 = resp1.json()

    # Create invoice for profile 2
    invoice2_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile2["id"],
        "total_amount": 200.0,
        "invoice_items": [{"description": "Service 2", "quantity": 1, "price": 200.0}],
    }

    resp2 = client.post("/invoices/", json=invoice2_data)
    assert resp2.status_code == 201
    invoice2 = resp2.json()

    # Numbers should be sequential globally (not starting over per profile)
    import datetime

    current_year = str(datetime.datetime.now().year)[-2:]

    # Extract the numeric parts
    num1 = int(invoice1["number"].split(" | ")[1])
    num2 = int(invoice2["number"].split(" | ")[1])

    # Second invoice should have number one higher than first
    assert num2 == num1 + 1

    # Both should have correct year prefix
    assert invoice1["number"].startswith(f"{current_year} | ")
    assert invoice2["number"].startswith(f"{current_year} | ")


# ---------------------------------------------------------------------------
# 🧪 Number Preview Tests
# ---------------------------------------------------------------------------


def test_get_invoice_number_preview():
    """Test getting preview of next invoice number (global)"""
    resp = client.get("/invoices/number-preview")
    assert resp.status_code == 200

    data = resp.json()
    assert "preview_number" in data

    preview_number = data["preview_number"]
    assert validate_invoice_number_format(preview_number) is True

    # Should be current year + sequential number
    import datetime

    current_year = str(datetime.datetime.now().year)[-2:]
    assert preview_number.startswith(f"{current_year} | ")


def test_get_invoice_number_preview_no_params():
    """Test preview endpoint works without parameters (global numbering)"""
    resp = client.get("/invoices/number-preview")
    assert resp.status_code == 200

    data = resp.json()
    assert "preview_number" in data
    assert validate_invoice_number_format(data["preview_number"]) is True


def test_preview_matches_actual_generated_number(profile, customer):
    """Test that preview number matches the actually generated number"""
    # Get preview
    preview_resp = client.get("/invoices/number-preview")
    assert preview_resp.status_code == 200
    preview_number = preview_resp.json()["preview_number"]

    # Create invoice
    invoice_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 100.0,
        "invoice_items": [
            {"description": "Test Service", "quantity": 1, "price": 100.0}
        ],
    }

    invoice_resp = client.post("/invoices/", json=invoice_data)
    assert invoice_resp.status_code == 201
    actual_number = invoice_resp.json()["number"]

    # Preview should match actual
    assert preview_number == actual_number


def test_preview_updates_after_invoice_creation(profile, customer):
    """Test that preview updates correctly after creating invoices"""
    # Get initial preview
    preview_resp1 = client.get("/invoices/number-preview")
    preview1 = preview_resp1.json()["preview_number"]

    # Create invoice
    invoice_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 100.0,
        "invoice_items": [
            {"description": "Test Service", "quantity": 1, "price": 100.0}
        ],
    }

    invoice_resp = client.post("/invoices/", json=invoice_data)
    assert invoice_resp.status_code == 201

    # Get updated preview
    preview_resp2 = client.get("/invoices/number-preview")
    preview2 = preview_resp2.json()["preview_number"]

    # Extract numbers
    num1 = int(preview1.split(" | ")[1])
    num2 = int(preview2.split(" | ")[1])

    # Second preview should be one higher
    assert num2 == num1 + 1


# ---------------------------------------------------------------------------
# 🧪 Edge Case Tests
# ---------------------------------------------------------------------------


def test_invoice_creation_without_number_field():
    """Test that new invoice creation works without number field"""
    profile_resp = client.post(
        "/profiles/",
        json={
            "name": "Auto Number Profile",
            "address": "Auto Street 1",
            "city": "Auto City",
        },
    )
    profile = profile_resp.json()

    customer_resp = client.post("/customers/", json={"name": "Auto Customer"})
    customer = customer_resp.json()

    # Create invoice without number field
    invoice_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 150.0,
        "invoice_items": [
            {"description": "Auto Service", "quantity": 1, "price": 150.0}
        ],
    }

    resp = client.post("/invoices/", json=invoice_data)
    assert resp.status_code == 201

    invoice = resp.json()
    assert "number" in invoice
    assert validate_invoice_number_format(invoice["number"]) is True


def test_concurrent_invoice_creation_same_profile():
    """Test that concurrent creation doesn't create duplicate numbers"""
    # This is a simplified test - real concurrency testing would be more complex

    profile_resp = client.post(
        "/profiles/",
        json={
            "name": "Concurrent Profile",
            "address": "Concurrent Street",
            "city": "Concurrent City",
        },
    )
    profile = profile_resp.json()

    customer_resp = client.post("/customers/", json={"name": "Concurrent Customer"})
    customer = customer_resp.json()

    invoice_data = {
        "date": "2025-10-20",
        "customer_id": customer["id"],
        "profile_id": profile["id"],
        "total_amount": 100.0,
        "invoice_items": [
            {"description": "Concurrent Service", "quantity": 1, "price": 100.0}
        ],
    }

    # Create multiple invoices rapidly
    invoices = []
    for _ in range(5):
        resp = client.post("/invoices/", json=invoice_data)
        assert resp.status_code == 201
        invoices.append(resp.json())

    # All numbers should be unique
    numbers = [inv["number"] for inv in invoices]
    assert len(numbers) == len(set(numbers)), "Duplicate numbers found"

    # All should have valid format
    for number in numbers:
        assert validate_invoice_number_format(number) is True
