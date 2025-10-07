from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

TEST_PROFILE = {
    "name": "Invoice Profile",
    "address": "123 Invoice Street",
    "city": "Invoice City",
}
TEST_CUSTOMER = {"name": "Invoice Customer"}
TEST_INVOICE = {
    "number": "25|113",
    "date": "2025-09-10",
    "profile_id": None,
    "customer_id": None,
    "invoice_items": [],
    "include_tax": False,
    "total_amount": 0.0,
}


def test_create_invoice():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    # 2. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]
    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["customer_id"] = customer_id
    invoice["invoice_items"] = [{"description": "Item 1", "quantity": 1, "price": 24.0}]
    invoice["total_amount"] = 24.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 201
    invoice_data = invoice_response.json()

    assert invoice_data["number"] == invoice["number"]
    assert invoice_data["profile_id"] == profile_id
    assert invoice_data["customer_id"] == customer_id
    assert invoice_data["total_amount"] == invoice["total_amount"]
    assert invoice_data["date"] == invoice["date"]
    assert (
        invoice_data["invoice_items"][0]["description"]
        == invoice["invoice_items"][0]["description"]
    )
    assert (
        invoice_data["invoice_items"][0]["quantity"]
        == invoice["invoice_items"][0]["quantity"]
    )
    assert (
        invoice_data["invoice_items"][0]["price"]
        == invoice["invoice_items"][0]["price"]
    )

def test_create_invoice_with_tax_fields():
    profile_response = client.post("/profiles/", json={"name": "TaxTest", "address": "A", "city": "B"})
    profile_id = profile_response.json()["id"]

    customer_response = client.post("/customers/", json={"name": "TaxCustomer"})
    customer_id = customer_response.json()["id"]

    invoice_data = {
        "number": "25|999",
        "date": "2025-09-01",
        "customer_id": customer_id,
        "profile_id": profile_id,
        "total_amount": 100.00,
        "include_tax": True,
        "tax_rate": 0.19,
        "is_gross_amount": True,
        "invoice_items": [{"description": "Cut", "quantity": 1, "price": 100.00}]
    }

    resp = client.post("/invoices/", json=invoice_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["include_tax"] is True
    assert data["tax_rate"] == 0.19
    assert data["is_gross_amount"] is True


def test_create_invoice_without_invoice_item():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    # 2. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]
    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["customer_id"] = customer_id
    invoice["total_amount"] = 0.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 422


def test_create_invoice_without_profile():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["total_amount"] = 0.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 422


def test_create_invoice_without_customer():
    # 1. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["customer_id"] = customer_id
    invoice["total_amount"] = 0.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 422


def test_create_invoice_with_wrong_profile():
    # 1. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = 9999  # Non-existent profile ID
    invoice["customer_id"] = customer_id
    invoice["invoice_items"] = [{"description": "Item 1", "quantity": 1, "price": 24.0}]
    invoice["total_amount"] = 24.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 400
    assert invoice_response.json() == {"detail": "Profile does not exist."}


def test_create_invoice_with_wrong_customer():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["customer_id"] = 9999  # Non-existent customer ID
    invoice["invoice_items"] = [{"description": "Item 1", "quantity": 1, "price": 24.0}]
    invoice["total_amount"] = 24.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    assert invoice_response.status_code == 400
    assert invoice_response.json() == {"detail": "Customer does not exist."}


def test_get_invoice():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    # 2. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["customer_id"] = customer_id
    invoice["invoice_items"] = [{"description": "Item 1", "quantity": 1, "price": 24.0}]
    invoice["total_amount"] = 24.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    invoice_id = invoice_response.json()["id"]

    # 4. Get invoice
    get_response = client.get(f"/invoices/{invoice_id}")
    assert get_response.status_code == 200
    invoice_data = get_response.json()

    assert invoice_data["id"] == invoice_id
    assert invoice_data["number"] == invoice["number"]
    assert invoice_data["profile_id"] == profile_id
    assert invoice_data["customer_id"] == customer_id
    assert invoice_data["total_amount"] == invoice["total_amount"]
    assert invoice_data["date"] == invoice["date"]
    assert (
        invoice_data["invoice_items"][0]["description"]
        == invoice["invoice_items"][0]["description"]
    )
    assert (
        invoice_data["invoice_items"][0]["quantity"]
        == invoice["invoice_items"][0]["quantity"]
    )
    assert (
        invoice_data["invoice_items"][0]["price"]
        == invoice["invoice_items"][0]["price"]
    )


def test_get_invoice_with_invalid_id():
    response = client.get("/invoices/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Invoice not found."}


def test_get_invoice_list():
    response = client.get("/invoices/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_delete_invoice():
    # 1. Create profile
    profile_response = client.post("/profiles/", json=TEST_PROFILE)
    profile_id = profile_response.json()["id"]

    # 2. Create customer
    customer_response = client.post("/customers/", json=TEST_CUSTOMER)
    customer_id = customer_response.json()["id"]

    invoice = TEST_INVOICE.copy()
    invoice["profile_id"] = profile_id
    invoice["customer_id"] = customer_id
    invoice["invoice_items"] = [{"description": "Item 1", "quantity": 1, "price": 24.0}]
    invoice["total_amount"] = 24.0
    # 3. Create invoice
    invoice_response = client.post("/invoices/", json=invoice)
    invoice_id = invoice_response.json()["id"]

    # 4. Delete invoice
    delete_response = client.delete(f"/invoices/{invoice_id}")
    assert delete_response.status_code == 204

    # 5. Verify deletion
    get_response = client.get(f"/invoices/{invoice_id}")
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": "Invoice not found."}


def test_delete_invoice_with_invalid_id():
    response = client.delete("/invoices/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Invoice not found."}
