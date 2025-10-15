from typing import List, Optional

from sqlmodel import SQLModel


class SummaryInvoiceRead(SQLModel):
    """Ausgabemodell für GET /summary-invoices"""

    id: int
    range_text: str
    date: str
    profile_id: int
    total_net: float
    total_tax: float
    total_gross: float
    invoice_ids: Optional[List[int]] = None
