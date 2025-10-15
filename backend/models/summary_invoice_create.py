from typing import List

from sqlmodel import SQLModel


class SummaryInvoiceCreate(SQLModel):
    """Eingabemodell für POST /summary-invoices"""

    profile_id: int
    invoice_ids: List[int]
