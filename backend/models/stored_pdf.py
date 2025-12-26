from datetime import datetime
from typing import Optional

from sqlmodel import Field, Index, SQLModel


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
    """Database model for stored PDFs with unique constraints to prevent duplicates"""

    __tablename__ = "stored_pdfs"
    __table_args__ = (
        Index("ix_stored_pdfs_invoice_id", "invoice_id", unique=True),
        Index("ix_stored_pdfs_summary_invoice_id", "summary_invoice_id", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)


class StoredPDFCreate(StoredPDFBase):
    """Model for creating a stored PDF"""

    pass


class StoredPDFRead(StoredPDFBase):
    """Model for reading a stored PDF"""

    id: int
