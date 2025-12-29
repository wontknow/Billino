from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Customer
from models.table_models import (
    GlobalSearch,
    PaginatedResponse,
    SortDirection,
    SortField,
)
from services.filter_service import FilterService, create_paginated_response, paginate
from utils import logger
from utils.router_utils import parse_filter_params, parse_sort_params

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
    - `note` (string, optional): Customer notes (e.g., color preferences, special instructions)

    **Returns:**
    - Customer object with assigned ID

    **Example Request:**
    ```json
    {
        "name": "John Doe",
        "address": "123 Main Street",
        "city": "Berlin",
        "note": "Prefers blue color scheme"
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "name": "John Doe",
        "address": "123 Main Street",
        "city": "Berlin",
        "note": "Prefers blue color scheme"
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


@router.get("/", response_model=PaginatedResponse[Customer])
def list_customers(
    session: Session = Depends(get_session),
    # Filterung
    filter: list[str] = Query(
        None,
        description="Filters as 'field:operator:value'. Example: 'name:contains:John' or 'id:equals:1'",
    ),
    # Sortierung
    sort: list[str] = Query(
        None,
        description="Sort order as 'field:direction'. Example: 'name:asc' or 'created_at:desc'",
    ),
    # Globale Suche
    q: str = Query(
        None,
        min_length=2,
        description="Global search query (searches in name, address, city, note)",
    ),
    # Paginierung
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
):
    """
    List customers with advanced filtering, sorting, and pagination.

    Supports multi-column filtering, global search, and stable sorting.

    **Query Parameters:**

    **Filtering:**
    - `filter` (repeatable): Filter as 'field:operator:value'
      - Fields: `id`, `name`, `address`, `city`, `note`
      - Operators: `contains`, `startsWith`, `exact`, `equals`, `between`, `in`, `gt`, `lt`, `gte`, `lte`
      - Examples:
        - `filter=name:contains:John` (contains 'John' case-insensitive)
        - `filter=name:startsWith:A` (starts with 'A')
        - `filter=id:equals:5` (exact match)
        - `filter=id:gt:10` (greater than 10)

    **Sorting:**
    - `sort` (repeatable): Sort as 'field:direction'
      - Fields: `id`, `name`, `address`, `city`, `note`
      - Direction: `asc` (ascending) or `desc` (descending)
      - Examples:
        - `sort=name:asc` (sort by name ascending)
        - `sort=id:desc` (sort by ID descending)
        - Multiple: `sort=name:asc&sort=id:asc` (multi-column sort)

    **Global Search:**
    - `q` (string, optional): Search query (min 2 characters)
      - Searches across: `name`, `address`, `city`, `note` (case-insensitive)
      - Example: `q=Berlin`

    **Pagination:**
    - `page` (integer, default=1): Page number (1-indexed)
    - `pageSize` (integer, default=10, max=100): Items per page

    **Returns:**
    - PaginatedResponse with items, total count, page info

    **Example Requests:**
    ```
    GET /customers/?page=1&pageSize=10
    GET /customers/?filter=name:contains:John&sort=name:asc&page=1
    GET /customers/?q=Berlin&pageSize=20
    GET /customers/?filter=id:gt:5&filter=name:startsWith:A&sort=id:desc
    ```

    **Example Response:**
    ```json
    {
        "items": [
            {"id": 1, "name": "John Doe", "address": "123 Main", "city": "Berlin", "note": null},
            {"id": 2, "name": "Jane Smith", "address": "456 Oak", "city": "Munich", "note": null}
        ],
        "total": 2,
        "page": 1,
        "pageSize": 10,
        "pageCount": 1
    }
    ```
    """
    logger.debug("👥 GET /customers - Listing with filters/sort/pagination")

    # Parse query parameters using shared utilities
    filters = parse_filter_params(filter)
    sort_fields = parse_sort_params(sort)

    try:
        # Start with base select
        stmt = select(Customer)

        # Apply Filters
        if filters:
            stmt = FilterService.apply_filters(
                stmt,
                filters,
                Customer,
                allowed_fields={"id", "name", "address", "city", "note"},
            )

        # Apply Global Search
        if q:
            stmt = FilterService.apply_global_search(
                stmt,
                GlobalSearch(query=q),
                Customer,
                search_fields={"name", "address", "city", "note"},
            )

        # Apply Sort
        sort_fields_to_apply = (
            sort_fields
            if sort_fields
            else [SortField(field="id", direction=SortDirection.ASC)]
        )
        stmt = FilterService.apply_sort(
            stmt,
            sort_fields_to_apply,
            Customer,
            primary_key_field="id",
            allowed_fields={"id", "name", "address", "city", "note"},
        )

        # Paginate
        items, total = paginate(session, stmt, Customer, page=page, page_size=pageSize)

        response = create_paginated_response(items, total, page, pageSize)
        logger.info(f"✅ Retrieved {len(items)}/{total} customers")
        return response

    except ValueError as e:
        logger.error(f"❌ Invalid query parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


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
    - `note` (string or null): Customer notes (e.g., color preferences, special instructions)

    **Returns:**
    - Updated Customer object

    **Example Request:**
    ```json
    {
        "name": "John Doe Updated",
        "address": "456 New Street",
        "city": "Hamburg",
        "note": "Updated preference: now prefers red colors"
    }
    ```

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "name": "John Doe Updated",
        "address": "456 New Street",
        "city": "Hamburg",
        "note": "Updated preference: now prefers red colors"
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
    if customer.note != updated_customer.note:
        customer.note = updated_customer.note
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
