from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import (
    Customer,
    Invoice,
    InvoiceCreate,
    InvoiceItem,
    InvoiceItemRead,
    InvoiceRead,
    Profile,
    SummaryInvoiceCreate,
    SummaryInvoiceRead,
)
from models.table_models import (
    ColumnFilter,
    FilterOperator,
    GlobalSearch,
    PaginatedResponse,
    SortDirection,
    SortField,
)
from services import (
    create_summary_invoice,
    generate_next_invoice_number,
    get_preview_invoice_number,
)
from services.background_pdf_generator import BackgroundPDFGenerator
from services.filter_service import FilterService, create_paginated_response, paginate
from services.pdf_generation_service import generate_pdf_for_invoice
from utils import logger
from utils.router_utils import parse_filter_params, parse_sort_params

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("/number-preview")
def get_invoice_number_preview(session: Session = Depends(get_session)):
    """
    Get a preview of the next invoice number.

    Returns what the next automatically generated invoice number will be.
    Useful for frontend to show users what number their invoice will get.

    Note: Invoice numbers are sequential across all profiles (German tax law compliance).
    Format: "YY | NNN" (e.g., "25 | 001")

    **Returns:**
    - `preview_number` (string): The next invoice number in format "YY | NNN"

    **Example Response (200):**
    ```json
    {
        "preview_number": "25 | 042"
    }
    ```
    """
    logger.debug("🔢 GET /invoices/number-preview - Fetching next invoice number")
    next_number = get_preview_invoice_number(session)
    logger.debug(f"✅ Next invoice number preview: {next_number}")
    return {"preview_number": next_number}


@router.post("/", response_model=InvoiceRead, status_code=201)
def create_invoice(invoice: InvoiceCreate, session: Session = Depends(get_session)):
    """
    Create a new invoice.

    Creates a new invoice with automatic invoice number generation. The request must include
    at least one invoice item. The sum of invoice items must match the total_amount (within 0.01 tolerance).

    **Request Body:**
    - `date` (string, required): Invoice date (format: "YYYY-MM-DD")
    - `customer_id` (integer, required): ID of the customer
    - `profile_id` (integer, required): ID of the seller profile
    - `total_amount` (float, required): Total amount (must match sum of items)
    - `invoice_items` (array, required): At least one invoice item with:
        - `quantity` (integer): Quantity of items
        - `description` (string): Item description
        - `price` (float): Price per item
        - `tax_rate` (float, optional): Individual tax rate for this item
    - `include_tax` (boolean, optional): Whether to include VAT. If not provided, inherits from profile
    - `tax_rate` (float, optional): VAT rate as decimal (0.19 for 19%). Required if include_tax=true
    - `is_gross_amount` (boolean, optional): Whether total_amount is gross or net (default: false = net)

    **Returns:**
    - InvoiceRead object with assigned invoice number and ID

    **Example Request:**
    ```json
    {
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "invoice_items": [
            {
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00
            }
        ],
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "number": "25 | 001",
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true,
        "invoice_items": [
            {
                "id": 1,
                "invoice_id": 1,
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00,
                "tax_rate": null
            }
        ]
    }
    ```
    """
    logger.debug(
        f"📝 POST /invoices - Creating invoice for customer_id={invoice.customer_id}, profile_id={invoice.profile_id}"
    )

    profile = session.get(Profile, invoice.profile_id)
    customer = session.get(Customer, invoice.customer_id)
    # Profile und Customer validieren
    if not profile:
        logger.error(f"❌ Profile {invoice.profile_id} not found")
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "loc": ["body", "profile_id"],
                    "msg": "Profile does not exist.",
                    "type": "value_error",
                }
            ],
        )
    if not customer:
        logger.error(f"❌ Customer {invoice.customer_id} not found")
        raise HTTPException(
            status_code=400,
            detail=[
                {
                    "loc": ["body", "customer_id"],
                    "msg": "Customer does not exist.",
                    "type": "value_error",
                }
            ],
        )

    # Generate next invoice number automatically (globally, not per profile)
    invoice_number = generate_next_invoice_number(session)
    logger.debug(f"🔢 Generated invoice number: {invoice_number}")

    # Vererbe Steuersatz vom Profil, wenn nicht explizit angegeben
    if invoice.include_tax is None:
        invoice.include_tax = profile.include_tax

    if invoice.include_tax:
        if invoice.tax_rate is None:
            invoice.tax_rate = profile.default_tax_rate
    else:
        invoice.tax_rate = 0.0

    # 1. Summenprüfung vor DB-Aktion
    calculated_total = round(
        sum(item.quantity * item.price for item in invoice.invoice_items), 2
    )
    tolerance = 0.01
    difference = round(calculated_total - invoice.total_amount, 2)
    logger.debug(
        f"💰 Total validation - Calculated: {calculated_total}, Expected: {invoice.total_amount}, Diff: {difference}"
    )

    if difference >= tolerance:
        logger.error(f"❌ Total amount exceeds expected by {difference}")
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", "total_amount"],
                    "msg": "Sum of invoice items exceeds total_amount by more than 0.01.",
                    "type": "value_error",
                }
            ],
        )

    if -difference >= tolerance:
        logger.error(f"❌ Total amount is less than expected by {-difference}")
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["body", "total_amount"],
                    "msg": "Sum of invoice items is less than total_amount by more than 0.01.",
                    "type": "value_error",
                }
            ],
        )

    # Invoice + Items in einer Transaktion anlegen
    db_invoice = Invoice(
        number=invoice_number,  # Use generated number
        date=invoice.date,
        customer_id=invoice.customer_id,
        profile_id=invoice.profile_id,
        include_tax=invoice.include_tax,
        tax_rate=invoice.tax_rate,
        is_gross_amount=invoice.is_gross_amount,
        total_amount=invoice.total_amount,
    )
    session.add(db_invoice)
    session.flush()  # erzeugt ID für Invoice, ohne Commit

    db_items: list[InvoiceItem] = []
    for item in invoice.invoice_items:
        db_item = InvoiceItem(
            invoice_id=db_invoice.id,
            quantity=item.quantity,
            description=item.description,
            price=item.price,
        )
        session.add(db_item)
        db_items.append(db_item)

    session.commit()
    session.refresh(db_invoice)
    for db_item in db_items:
        session.refresh(db_item)

    logger.info(
        f"✅ Invoice {invoice_number} created successfully (id={db_invoice.id})"
    )

    # Trigger PDF generation asynchronously in background thread
    logger.debug(
        f"🖨️ Starting background thread for PDF generation (invoice {db_invoice.id})..."
    )
    BackgroundPDFGenerator.generate_in_background(
        pdf_generation_func=generate_pdf_for_invoice,
        entity_id=db_invoice.id,
        entity_type="invoice",
    )

    # Compute totals for response
    rate = db_invoice.tax_rate or 0.0
    include_tax_flag = bool(db_invoice.include_tax) and rate > 0.0
    if not include_tax_flag:
        net = db_invoice.total_amount
        tax = 0.0
        gross = db_invoice.total_amount
    elif db_invoice.is_gross_amount:
        gross = db_invoice.total_amount
        net = gross / (1 + rate)
        tax = gross - net
    else:
        net = db_invoice.total_amount
        tax = net * rate
        gross = net + tax
    net = round(net, 2)
    tax = round(tax, 2)
    gross = round(gross, 2)

    customer = session.get(Customer, db_invoice.customer_id)

    return InvoiceRead(
        id=db_invoice.id,
        number=db_invoice.number,
        date=db_invoice.date,
        customer_id=db_invoice.customer_id,
        profile_id=db_invoice.profile_id,
        include_tax=db_invoice.include_tax,
        tax_rate=db_invoice.tax_rate,
        is_gross_amount=db_invoice.is_gross_amount,
        total_amount=db_invoice.total_amount,
        total_net=net,
        total_tax=tax,
        total_gross=gross,
        customer_name=(customer.name if customer else None),
        invoice_items=[
            InvoiceItemRead(
                id=item.id,
                invoice_id=item.invoice_id,
                quantity=item.quantity,
                description=item.description,
                price=item.price,
            )
            for item in db_items
        ],
    )


@router.get("/", response_model=PaginatedResponse[InvoiceRead])
def read_invoices(
    session: Session = Depends(get_session),
    # Filterung
    filter: list[str] = Query(
        None,
        description="Filters as 'field:operator:value'. Example: 'number:contains:25'",
    ),
    # Sortierung
    sort: list[str] = Query(
        None,
        description="Sort order as 'field:direction'. Example: 'date:desc'",
    ),
    # Globale Suche
    q: str = Query(
        None,
        min_length=2,
        description="Global search query (searches in number, customer_name)",
    ),
    # Paginierung
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
):
    """
    List invoices with advanced filtering, sorting, and pagination.

    **Query Parameters:**

    **Filtering:**
    - `filter` (repeatable): Filter as 'field:operator:value'
      - Fields: `id`, `number`, `date`, `customer_id`, `profile_id`, `total_amount`, `include_tax`, `tax_rate`
      - Examples: `filter=number:contains:25`, `filter=date:gte:2025-01-01`

    **Sorting:**
    - `sort` (repeatable): Sort as 'field:direction'
      - Examples: `sort=date:desc`, `sort=number:asc`

    **Global Search:**
    - `q` (string, optional): Searches in number and related customer name

    **Pagination:**
    - `page` (integer, default=1): Page number
    - `pageSize` (integer, default=10, max=100): Items per page

    **Returns:**
    - PaginatedResponse with InvoiceRead items (including computed tax totals)
    """
    logger.debug("📄 GET /invoices - Listing with filters/sort/pagination")

    filters = parse_filter_params(filter)
    sort_fields = parse_sort_params(sort)

    # Map date_from and date_to filters to date filters with gte/lte operators
    # Also convert exact date filter to equals
    mapped_filters = []
    for f in filters or []:
        if f.field == "date_from":
            mapped_filters.append(
                ColumnFilter(field="date", operator=FilterOperator.GTE, value=f.value)
            )
        elif f.field == "date_to":
            mapped_filters.append(
                ColumnFilter(field="date", operator=FilterOperator.LTE, value=f.value)
            )
        elif f.field == "date" and f.operator == FilterOperator.EXACT:
            # Convert exact date filter to equals for proper date comparison
            mapped_filters.append(
                ColumnFilter(
                    field="date", operator=FilterOperator.EQUALS, value=f.value
                )
            )
        else:
            mapped_filters.append(f)
    filters = mapped_filters

    try:
        stmt = select(Invoice)
        joined_customer = False
        joined_profile = False

        # Sonderfall-Filter: customer_name und profile_name (benötigen Joins)
        customer_name_filters = (
            [f for f in filters if f.field == "customer_name"] if filters else []
        )
        profile_name_filters = (
            [f for f in filters if f.field == "profile_name"] if filters else []
        )
        other_filters = [
            f
            for f in (filters or [])
            if f.field not in ("customer_name", "profile_name")
        ]

        if customer_name_filters:
            # Join auf Customer und Filter auf Customer.name anwenden
            from sqlalchemy import and_  # lokal um globale Imports minimal zu halten

            stmt = stmt.join(Customer, Invoice.customer_id == Customer.id)
            joined_customer = True
            for f in customer_name_filters:
                val = str(f.value)
                op = f.operator
                if op == "contains":
                    condition = Customer.name.ilike(
                        f"%{FilterService.escape_wildcards(val)}%", escape="\\"
                    )
                elif op in ("exact", "equals"):
                    # exact: case-insensitive Gleichheit via ilike
                    condition = Customer.name.ilike(
                        FilterService.escape_wildcards(val), escape="\\"
                    )
                elif op == "starts_with":
                    condition = Customer.name.ilike(
                        f"{FilterService.escape_wildcards(val)}%", escape="\\"
                    )
                else:
                    raise ValueError(f"Operator '{op}' not supported for customer_name")
                stmt = stmt.where(condition)
            # Duplikate vermeiden, falls mehrere Invoices den gleichen Customer haben
            stmt = stmt.distinct()

        if profile_name_filters:
            # Join auf Profile und Filter auf Profile.name anwenden
            stmt = stmt.join(Profile, Invoice.profile_id == Profile.id)
            joined_profile = True
            for f in profile_name_filters:
                val = str(f.value)
                op = f.operator
                if op == "contains":
                    condition = Profile.name.ilike(
                        f"%{FilterService.escape_wildcards(val)}%", escape="\\"
                    )
                elif op in ("exact", "equals"):
                    condition = Profile.name.ilike(
                        FilterService.escape_wildcards(val), escape="\\"
                    )
                elif op == "starts_with":
                    condition = Profile.name.ilike(
                        f"{FilterService.escape_wildcards(val)}%", escape="\\"
                    )
                else:
                    raise ValueError(f"Operator '{op}' not supported for profile_name")
                stmt = stmt.where(condition)
            stmt = stmt.distinct()

        if other_filters:
            stmt = FilterService.apply_filters(
                stmt,
                other_filters,
                Invoice,
                allowed_fields={
                    "id",
                    "number",
                    "date",
                    "customer_id",
                    "profile_id",
                    "total_amount",
                    "include_tax",
                    "tax_rate",
                },
            )

        if q:
            # Globale Suche: Wir müssen hier nur auf Invoice-Felder durchsuchen
            # (customer_name ist computed, nicht in DB)
            stmt = FilterService.apply_global_search(
                stmt,
                GlobalSearch(query=q),
                Invoice,
                search_fields={"number"},
            )

        # Sortierung anwenden, inkl. Sonderfall: customer_name und profile_name (Joins + ORDER BY)
        sort_fields_to_apply = (
            sort_fields
            if sort_fields
            else [SortField(field="id", direction=SortDirection.DESC)]
        )

        customer_name_sorts = [
            s for s in sort_fields_to_apply if s.field == "customer_name"
        ]
        profile_name_sorts = [
            s for s in sort_fields_to_apply if s.field == "profile_name"
        ]
        other_sorts = [
            s
            for s in sort_fields_to_apply
            if s.field not in ("customer_name", "profile_name")
        ]

        # Falls nach customer_name sortiert werden soll, Join sicherstellen und ORDER BY auf Customer.name setzen
        if customer_name_sorts:
            if not joined_customer:
                stmt = stmt.join(Customer, Invoice.customer_id == Customer.id)
                joined_customer = True
            for s in customer_name_sorts:
                if s.direction == SortDirection.ASC:
                    stmt = stmt.order_by(Customer.name.asc())
                else:
                    stmt = stmt.order_by(Customer.name.desc())

        # Falls nach profile_name sortiert werden soll, Join sicherstellen und ORDER BY auf Profile.name setzen
        if profile_name_sorts:
            if not joined_profile:
                stmt = stmt.join(Profile, Invoice.profile_id == Profile.id)
                joined_profile = True
            for s in profile_name_sorts:
                if s.direction == SortDirection.ASC:
                    stmt = stmt.order_by(Profile.name.asc())
                else:
                    stmt = stmt.order_by(Profile.name.desc())

        # Übrige Sortierfelder normal anwenden (nur erlaubte Invoice-Felder)
        stmt = FilterService.apply_sort(
            stmt,
            other_sorts,
            Invoice,
            primary_key_field="id",
            allowed_fields={
                "id",
                "number",
                "date",
                "customer_id",
                "profile_id",
                "total_amount",
                "include_tax",
                "tax_rate",
            },
        )

        invoices, total = paginate(
            session, stmt, Invoice, page=page, page_size=pageSize
        )

        # Compute InvoiceRead objects with tax calculations
        result = []
        for inv in invoices:
            items = session.exec(
                select(InvoiceItem).where(InvoiceItem.invoice_id == inv.id)
            ).all()

            # Compute totals
            rate = inv.tax_rate or 0.0
            include_tax_flag = bool(inv.include_tax) and rate > 0.0
            if not include_tax_flag:
                net = inv.total_amount
                tax = 0.0
                gross = inv.total_amount
            elif inv.is_gross_amount:
                gross = inv.total_amount
                net = gross / (1 + rate)
                tax = gross - net
            else:
                net = inv.total_amount
                tax = net * rate
                gross = net + tax

            net = round(net, 2)
            tax = round(tax, 2)
            gross = round(gross, 2)

            customer = session.get(Customer, inv.customer_id)
            profile = session.get(Profile, inv.profile_id)

            result.append(
                InvoiceRead(
                    id=inv.id,
                    number=inv.number,
                    date=inv.date,
                    customer_id=inv.customer_id,
                    profile_id=inv.profile_id,
                    include_tax=inv.include_tax,
                    tax_rate=inv.tax_rate,
                    is_gross_amount=inv.is_gross_amount,
                    total_amount=inv.total_amount,
                    total_net=net,
                    total_tax=tax,
                    total_gross=gross,
                    customer_name=(customer.name if customer else None),
                    profile_name=(profile.name if profile else None),
                    invoice_items=[
                        InvoiceItemRead(
                            id=item.id,
                            invoice_id=item.invoice_id,
                            quantity=item.quantity,
                            description=item.description,
                            price=item.price,
                        )
                        for item in items
                    ],
                )
            )

        response = create_paginated_response(result, total, page, pageSize)
        logger.info(f"✅ Retrieved {len(result)}/{total} invoices")
        return response

    except ValueError as e:
        logger.error(f"❌ Invalid query parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, session: Session = Depends(get_session)):
    """
    Get a single invoice by ID.

    Retrieves detailed information about a specific invoice including all line items.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice to retrieve

    **Returns:**
    - InvoiceRead object with all related invoice items

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "number": "25 | 001",
        "date": "2025-12-19",
        "customer_id": 1,
        "profile_id": 1,
        "total_amount": 119.00,
        "include_tax": true,
        "tax_rate": 0.19,
        "is_gross_amount": true,
        "invoice_items": [
            {
                "id": 1,
                "invoice_id": 1,
                "quantity": 2,
                "description": "Consulting Service",
                "price": 50.00,
                "tax_rate": null
            }
        ]
    }
    ```
    """
    logger.debug(f"📖 GET /invoices/{invoice_id} - Fetching invoice")
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        logger.error(f"❌ Invoice {invoice_id} not found")
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "invoice_id"],
                    "msg": "Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    logger.debug(f"✅ Invoice {invoice_id} fetched with {len(items)} items")
    # Compute single totals
    rate = invoice.tax_rate or 0.0
    include_tax_flag = bool(invoice.include_tax) and rate > 0.0
    if not include_tax_flag:
        net = invoice.total_amount
        tax = 0.0
        gross = invoice.total_amount
    elif invoice.is_gross_amount:
        gross = invoice.total_amount
        net = gross / (1 + rate)
        tax = gross - net
    else:
        net = invoice.total_amount
        tax = net * rate
        gross = net + tax
    net = round(net, 2)
    tax = round(tax, 2)
    gross = round(gross, 2)

    cust = session.get(Customer, invoice.customer_id)
    prof = session.get(Profile, invoice.profile_id)

    return InvoiceRead(
        id=invoice.id,
        number=invoice.number,
        date=invoice.date,
        customer_id=invoice.customer_id,
        profile_id=invoice.profile_id,
        include_tax=invoice.include_tax,
        tax_rate=invoice.tax_rate,
        is_gross_amount=invoice.is_gross_amount,
        total_amount=invoice.total_amount,
        total_net=net,
        total_tax=tax,
        total_gross=gross,
        customer_name=(cust.name if cust else None),
        profile_name=(prof.name if prof else None),
        invoice_items=[
            InvoiceItemRead(
                id=item.id,
                invoice_id=item.invoice_id,
                quantity=item.quantity,
                description=item.description,
                price=item.price,
            )
            for item in items
        ],
    )


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, session: Session = Depends(get_session)):
    """
    Delete an invoice.

    Removes an invoice and all its related line items from the database.

    **Path Parameters:**
    - `invoice_id` (integer, required): ID of the invoice to delete

    **Returns:**
    - No content (HTTP 204)

    **Note:** Deleting an invoice will also remove all associated invoice items.
    """
    logger.info(f"🗑️ DELETE /invoices/{invoice_id} - Deleting invoice")
    invoice = session.get(Invoice, invoice_id)
    if not invoice:
        logger.error(f"❌ Invoice {invoice_id} not found for deletion")
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "invoice_id"],
                    "msg": "Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    # Zuerst die zugehörigen Items löschen
    items = session.exec(
        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
    ).all()
    for item in items:
        session.delete(item)
    # Dann die Invoice selbst löschen
    session.delete(invoice)
    session.commit()
    logger.info(f"✅ Invoice {invoice_id} deleted successfully with {len(items)} items")
    return
