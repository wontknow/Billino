from typing import List

from pydantic import model_validator
from sqlmodel import SQLModel


class SummaryInvoiceCreate(SQLModel):
    """Eingabemodell für POST /summary-invoices"""

    profile_id: int
    invoice_ids: List[int]

    @model_validator(mode="after")
    def validate_summary(self):
        if not self.invoice_ids or len(self.invoice_ids) == 0:
            raise ValueError("At least one invoice ID must be provided.")
        if not self.profile_id or self.profile_id <= 0:
            raise ValueError("A valid profile ID must be provided.")
        return self
