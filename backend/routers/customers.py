from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Customer
from utils import logger

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=Customer, status_code=201)
def create_customer(customer: Customer, session: Session = Depends(get_session)):
    """
    Create a new customer.

    Creates a new customer record in the database.

    **Request Body:**
    - `name` (string, required): Customer name (must not be empty)
    - `address` (string, optional): Customer address
    - `city` (string, optional): Customer city

    **Returns:**
    - Customer object with assigned ID

    **Example Request:**
    ```json
    {
        "name": "John Doe",
        "address": "123 Main Street",
        "city": "Berlin"
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "name": "John Doe",
        "address": "123 Main Street",
        "city": "Berlin"
    }
    ```
    """
    logger.debug(f"➕ POST /customers - Creating customer: {customer.name}")
    # verify body
    if not customer.name:
        logger.error("❌ Customer name is missing")
        raise HTTPException(status_code=400, detail="Name is required")
    session.add(customer)
    session.commit()
    session.refresh(customer)
    logger.info(
        f"✅ Customer created successfully (id={customer.id}, name={customer.name})"
    )
    return customer


@router.get("/", response_model=list[Customer])
def list_customers(session: Session = Depends(get_session)):
    """
    List all customers.

    Retrieves a list of all customers in the database.

    **Returns:**
    - List of Customer objects

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "name": "John Doe",
            "address": "123 Main Street",
            "city": "Berlin"
        },
        {
            "id": 2,
            "name": "Jane Smith",
            "address": "456 Oak Avenue",
            "city": "Munich"
        }
    ]
    ```
    """
    logger.debug("👥 GET /customers - Listing all customers")
    customers = session.exec(select(Customer)).all()
    logger.debug(f"✅ Found {len(customers)} customers")
    return customers


@router.get("/search", response_model=list[Customer])
def search_customers(
    q: str = Query(..., min_length=2, description="Search query (min. 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Max results (default=10, max=50)"),
    session: Session = Depends(get_session),
):
    """
    Search for customers by name (case-insensitive substring match).

    Performs a case-insensitive substring search on customer names.

    **Query Parameters:**
    - `q` (string, required): Search query (minimum 2 characters)
    - `limit` (integer, optional): Maximum number of results (default=10, max=50)

    **Returns:**
    - List of matching Customer objects (limited to max results)

    **Example Request:**
    ```
    GET /customers/search?q=john&limit=5
    ```

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "name": "John Doe",
            "address": "123 Main Street",
            "city": "Berlin"
        }
    ]
    ```
    """
    logger.debug(f"🔍 GET /customers/search - Searching for: {q}")
    # Escape LIKE wildcards in user input
    escaped_q = q.replace("%", "\\%").replace("_", "\\_")
    statement = (
        select(Customer)
        .where(Customer.name.ilike(f"%{escaped_q}%", escape="\\"))
        .limit(limit)
    )
    customers = session.exec(statement).all()
    logger.debug(f"✅ Search found {len(customers)} customers")
    return customers


@router.put("/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    updated_customer: Customer,
    session: Session = Depends(get_session),
):
    """
    Update an existing customer.

    Updates the customer record with the data from the request body. This endpoint expects
    a full Customer object, and all fields sent in the request will overwrite the existing
    values (including when they are set to `null` or omitted in the JSON payload).

    **Path Parameters:**
    - `customer_id` (integer, required): ID of the customer to update

    **Request Body:**
    A full Customer representation. For correct behavior, all current field values should
    be supplied, as any field that differs from the stored value will be updated to the
    value provided in the request.
    - `name` (string): Customer name
    - `address` (string or null): Customer address
    - `city` (string or null): Customer city

    **Returns:**
    - Updated Customer object

    **Example Request:**
    ```json
    {
        "name": "John Doe Updated",
        "address": "456 New Street",
        "city": "Hamburg"
    }
    ```

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "name": "John Doe Updated",
        "address": "456 New Street",
        "city": "Hamburg"
    }
    ```
    """
    logger.info(f"✏️ PUT /customers/{customer_id} - Updating customer")
    customer = session.get(Customer, customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found for update")
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.name != updated_customer.name:
        customer.name = updated_customer.name
    if customer.address != updated_customer.address:
        customer.address = updated_customer.address
    if customer.city != updated_customer.city:
        customer.city = updated_customer.city
    session.add(customer)
    session.commit()
    session.refresh(customer)
    logger.info(f"✅ Customer {customer_id} updated successfully")
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, session: Session = Depends(get_session)):
    """
    Delete a customer.

    Removes the customer record from the database.

    **Path Parameters:**
    - `customer_id` (integer, required): ID of the customer to delete

    **Returns:**
    - No content (HTTP 204)

    **Example Response:**
    - Empty response body
    """
    logger.info(f"🗑️ DELETE /customers/{customer_id} - Deleting customer")
    customer = session.get(Customer, customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Customer not found")
    session.delete(customer)
    session.commit()
    logger.info(f"✅ Customer {customer_id} deleted successfully")
    return None
