from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List

class SummaryInvoice(SQLModel, table=True):
    __tablename__ = "summary_invoice"
    id: Optional[int] = Field(default=None, primary_key=True)
    range_text: str
    date: str
    profile_id: int = Field(foreign_key="profile.id")
    total_net: float
    total_tax: float
    total_gross: float

    invoices: List["SummaryInvoiceLink"] = Relationship(back_populates="summary_invoice")


class SummaryInvoiceLink(SQLModel, table=True):
    __tablename__ = "summary_invoice_link"
    id: Optional[int] = Field(default=None, primary_key=True)
    summary_invoice_id: int = Field(foreign_key="summary_invoice.id")
    invoice_id: int = Field(foreign_key="invoice.id")

    summary_invoice: Optional["SummaryInvoice"] = Relationship(back_populates="invoices")
