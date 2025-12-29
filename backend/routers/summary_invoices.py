### Summary Invoices
# Create, Read (list), Read (single), Delete

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlmodel import select

from database import get_session
from models import (
    Customer,
    Invoice,
    SummaryInvoice,
    SummaryInvoiceCreate,
    SummaryInvoiceLink,
    SummaryInvoiceRead,
)
from models.table_models import (
    GlobalSearch,
    PaginatedResponse,
    SortDirection,
    SortField,
)
from services import create_summary_invoice
from services.background_pdf_generator import BackgroundPDFGenerator
from services.filter_service import FilterService, create_paginated_response, paginate
from services.pdf_generation_service import generate_pdf_for_summary_invoice
from utils import logger
from utils.router_utils import parse_filter_params, parse_sort_params

LOG_DEV = os.getenv("ENV", "dev").lower() != "prod"

router = APIRouter(prefix="/summary-invoices", tags=["summary_invoices"])


@router.post("/", response_model=SummaryInvoiceRead, status_code=201)
def create_summary(
    summary: SummaryInvoiceCreate, session: Session = Depends(get_session)
):
    """
    Create a new summary invoice (Sammelrechnung).

    Combines multiple regular invoices into a single summary invoice.
    All invoices must belong to the same profile.

    **Request Body:**
    - `profile_id` (integer, required): ID of the seller profile
    - `invoice_ids` (array of integers, required): IDs of invoices to include (at least one)

    **Returns:**
    - SummaryInvoiceRead object with calculated totals

    **Example Request:**
    ```json
    {
        "profile_id": 1,
        "invoice_ids": [1, 2, 3]
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "range_text": "Invoice #1-3",
        "date": "2025-12-19",
        "profile_id": 1,
        "total_net": 100.00,
        "total_tax": 19.00,
        "total_gross": 119.00,
        "invoice_ids": [1, 2, 3]
    }
    ```
    """
    if LOG_DEV:
        logger.debug(
            "🧾 [DEV] POST /summary-invoices",
            {
                "profile_id": summary.profile_id,
                "invoice_count": len(summary.invoice_ids),
            },
        )

    try:
        summary_invoice = create_summary_invoice(session, summary)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=[{"loc": ["body"], "msg": str(e), "type": "value_error"}],
        )

    logger.info(
        "📄 Summary invoice created",
        {
            "id": summary_invoice.id,
            "profile_id": summary_invoice.profile_id,
            "invoice_count": len(summary.invoice_ids),
        },
    )

    # Trigger PDF generation asynchronously in background thread
    logger.debug(
        f"🖨️ Starting background thread for PDF generation (summary {summary_invoice.id})..."
    )

    recipient_name = getattr(summary, "recipient_name", None)
    recipient_customer_id = getattr(summary, "recipient_customer_id", None)

    # If only a recipient name was provided, try to resolve to a customer (create if not exists)
    if recipient_customer_id is None and recipient_name:
        from models import Customer

        existing = session.exec(
            select(Customer).where(Customer.name == recipient_name)
        ).first()
        if existing:
            recipient_customer_id = existing.id
        else:
            # Create a minimal customer record for the recipient
            new_customer = Customer(name=recipient_name)
            session.add(new_customer)
            session.commit()
            session.refresh(new_customer)
            recipient_customer_id = new_customer.id

    BackgroundPDFGenerator.generate_in_background(
        pdf_generation_func=generate_pdf_for_summary_invoice,
        entity_id=summary_invoice.id,
        entity_type="summary_invoice",
        thread_name_prefix="PDF-Summary",
        recipient_customer_id=recipient_customer_id,
    )

    return summary_invoice


@router.get("/", response_model=PaginatedResponse[SummaryInvoiceRead])
def list_summaries(
    session: Session = Depends(get_session),
    # Filterung
    filter: list[str] = Query(
        None,
        description="Filters as 'field:operator:value'. Example: 'profile_id:equals:1'",
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
        description="Global search query (searches in range_text)",
    ),
    # Paginierung
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    pageSize: int = Query(10, ge=1, le=100, description="Items per page (max 100)"),
):
    """
    List all summary invoices with filtering, sorting, and pagination.

    **Query Parameters:**

    **Filtering:**
    - `filter` (repeatable): Filter as 'field:operator:value'
      - Fields: `id`, `range_text`, `date`, `profile_id`, `total_net`, `total_tax`, `total_gross`
      - Examples: `filter=profile_id:equals:1`, `filter=date:gte:2025-01-01`

    **Sorting:**
    - `sort` (repeatable): Sort as 'field:direction'
      - Examples: `sort=date:desc`, `sort=range_text:asc`

    **Global Search:**
    - `q` (string, optional): Searches in range_text

    **Pagination:**
    - `page` (integer, default=1): Page number
    - `pageSize` (integer, default=10, max=100): Items per page

    **Returns:**
    - PaginatedResponse with SummaryInvoiceRead items
    """
    filters = parse_filter_params(filter)
    sort_fields = parse_sort_params(sort)

    try:
        stmt = select(SummaryInvoice)

        if filters:
            stmt = FilterService.apply_filters(
                stmt,
                filters,
                SummaryInvoice,
                allowed_fields={
                    "id",
                    "range_text",
                    "date",
                    "profile_id",
                    "total_net",
                    "total_tax",
                    "total_gross",
                    "recipient_customer_id",
                },
            )

        if q:
            stmt = FilterService.apply_global_search(
                stmt,
                GlobalSearch(query=q),
                SummaryInvoice,
                search_fields={"range_text"},
            )

        sort_fields_to_apply = (
            sort_fields
            if sort_fields
            else [SortField(field="id", direction=SortDirection.DESC)]
        )
        stmt = FilterService.apply_sort(
            stmt,
            sort_fields_to_apply,
            SummaryInvoice,
            primary_key_field="id",
            allowed_fields={
                "id",
                "range_text",
                "date",
                "profile_id",
                "total_net",
                "total_tax",
                "total_gross",
                "recipient_customer_id",
            },
        )

        summaries, total = paginate(
            session, stmt, SummaryInvoice, page=page, page_size=pageSize
        )

        # Build SummaryInvoiceRead objects
        summary_invoices = []
        for summary in summaries:
            # Get invoice IDs from links
            links = session.exec(
                select(SummaryInvoiceLink).where(
                    SummaryInvoiceLink.summary_invoice_id == summary.id
                )
            ).all()
            invoice_ids = [link.invoice_id for link in links]

            # Determine recipient_display_name
            recipient_display = None
            if summary.recipient_customer_id:
                cust = session.get(Customer, summary.recipient_customer_id)
                recipient_display = cust.name if cust else None
            else:
                # Fallback: join distinct customer names from linked invoices
                names = []
                for inv_id in invoice_ids:
                    inv = session.get(Invoice, inv_id)
                    if inv:
                        cust = session.get(Customer, inv.customer_id)
                        if cust and cust.name not in names:
                            names.append(cust.name)
                recipient_display = ", ".join(names) if names else None

            summary_invoices.append(
                SummaryInvoiceRead(
                    id=summary.id,
                    range_text=summary.range_text,
                    date=summary.date,
                    profile_id=summary.profile_id,
                    total_net=summary.total_net,
                    total_tax=summary.total_tax,
                    total_gross=summary.total_gross,
                    invoice_ids=invoice_ids,
                    recipient_customer_id=summary.recipient_customer_id,
                    recipient_display_name=recipient_display,
                )
            )

        response = create_paginated_response(summary_invoices, total, page, pageSize)
        logger.info(f"✅ Retrieved {len(summary_invoices)}/{total} summary invoices")
        return response

    except ValueError as e:
        logger.error(f"❌ Invalid query parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# get summaries by profile_id
@router.get("/by-profile/{profile_id}", response_model=list[SummaryInvoiceRead])
def list_summaries_by_profile(profile_id: int, session: Session = Depends(get_session)):
    """
    List all summary invoices for a specific profile.

    Retrieves all summary invoices created for a given seller profile.

    **Path Parameters:**
    - `profile_id` (integer, required): ID of the seller profile

    **Returns:**
    - List of SummaryInvoiceRead objects for the specified profile

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "range_text": "Invoice #1-3",
            "date": "2025-12-19",
            "profile_id": 1,
            "total_net": 100.00,
            "total_tax": 19.00,
            "total_gross": 119.00,
            "invoice_ids": [1, 2, 3]
        }
    ]
    ```
    """
    summaries = session.exec(
        select(SummaryInvoice).where(SummaryInvoice.profile_id == profile_id)
    ).all()
    if LOG_DEV:
        logger.debug(
            "🔍 [DEV] GET /summary-invoices/by-profile",
            {"profile_id": profile_id, "count": len(summaries)},
        )
    # Create list of SummaryInvoiceRead with invoice_ids from links
    summary_invoices = []
    for summary in summaries:
        # Get invoice IDs from links
        links = session.exec(
            select(SummaryInvoiceLink).where(
                SummaryInvoiceLink.summary_invoice_id == summary.id
            )
        ).all()
        invoice_ids = [link.invoice_id for link in links]

        summary_invoices.append(
            SummaryInvoiceRead(
                id=summary.id,
                range_text=summary.range_text,
                date=summary.date,
                profile_id=summary.profile_id,
                total_net=summary.total_net,
                total_tax=summary.total_tax,
                total_gross=summary.total_gross,
                invoice_ids=invoice_ids,
            )
        )
    return summary_invoices


@router.get("/{summary_id}", response_model=SummaryInvoiceRead)
def read_summary(summary_id: int, session: Session = Depends(get_session)):
    """
    Get a single summary invoice by ID.

    Retrieves detailed information about a specific summary invoice including its associated invoice IDs.

    **Path Parameters:**
    - `summary_id` (integer, required): ID of the summary invoice to retrieve

    **Returns:**
    - SummaryInvoiceRead object

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "range_text": "Invoice #1-3",
        "date": "2025-12-19",
        "profile_id": 1,
        "total_net": 100.00,
        "total_tax": 19.00,
        "total_gross": 119.00,
        "invoice_ids": [1, 2, 3]
    }
    ```
    """
    summary = session.get(SummaryInvoice, summary_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "summary_id"],
                    "msg": "Summary Invoice not found.",
                    "type": "value_error",
                }
            ],
        )

    # Get invoice IDs from links
    links = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary.id
        )
    ).all()
    invoice_ids = [link.invoice_id for link in links]

    # Determine recipient_display_name
    recipient_display = None
    if summary.recipient_customer_id:
        cust = session.get(Customer, summary.recipient_customer_id)
        recipient_display = cust.name if cust else None
    else:
        names = []
        for inv_id in invoice_ids:
            inv = session.get(Invoice, inv_id)
            if inv:
                cust = session.get(Customer, inv.customer_id)
                if cust and cust.name not in names:
                    names.append(cust.name)
        recipient_display = ", ".join(names) if names else None

    summary_invoice = SummaryInvoiceRead(
        id=summary.id,
        range_text=summary.range_text,
        date=summary.date,
        profile_id=summary.profile_id,
        total_net=summary.total_net,
        total_tax=summary.total_tax,
        total_gross=summary.total_gross,
        invoice_ids=invoice_ids,
        recipient_customer_id=summary.recipient_customer_id,
        recipient_display_name=recipient_display,
    )
    return summary_invoice


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, session: Session = Depends(get_session)):
    """
    Delete a summary invoice.

    Removes a summary invoice and all its associated links to regular invoices.
    Note: The regular invoices themselves are NOT deleted.

    **Path Parameters:**
    - `summary_id` (integer, required): ID of the summary invoice to delete

    **Returns:**
    - No content (HTTP 204)
    """
    summary = session.get(SummaryInvoice, summary_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "summary_id"],
                    "msg": "Summary Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    # Manually delete all SummaryInvoiceLink rows for this summary invoice
    links = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary_id
        )
    ).all()
    for link in links:
        session.delete(link)
    session.delete(summary)
    session.commit()
    return
