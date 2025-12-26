from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class StoredPDFBase(SQLModel):
    """Base model for stored PDFs"""

    type: str  # "invoice" or "summary_invoice"
    content: str  # Base64 encoded PDF content
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    invoice_id: Optional[int] = Field(default=None, foreign_key="invoice.id")
    summary_invoice_id: Optional[int] = Field(
        default=None, foreign_key="summary_invoice.id"
    )


class StoredPDF(StoredPDFBase, table=True):
    """Database model for stored PDFs with unique constraints to prevent duplicates

    Unique constraints:
    - invoice_id: Ensures each invoice can have at most one stored PDF
    - summary_invoice_id: Ensures each summary invoice can have at most one stored PDF

    Note: Both foreign keys are nullable to support different PDF types:
    - Invoice PDFs: invoice_id is set, summary_invoice_id is NULL
    - Summary invoice PDFs: summary_invoice_id is set, invoice_id is NULL
    - Other PDF types (e.g., a6_invoices): both may be NULL

    The unique constraints work correctly with NULLs in SQLite because:
    - Multiple NULL values are allowed in a unique column
    - The constraint only prevents duplicate non-NULL values
    - This allows multiple "other" PDFs while preventing duplicates for specific invoices
    """

    __tablename__ = "stored_pdfs"
    __table_args__ = (
        UniqueConstraint("invoice_id"),
        UniqueConstraint("summary_invoice_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)


class StoredPDFCreate(StoredPDFBase):
    """Model for creating a stored PDF"""

    pass


class StoredPDFRead(StoredPDFBase):
    """Model for reading a stored PDF"""

    id: int
