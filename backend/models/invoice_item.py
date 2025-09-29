from typing import Optional

from sqlmodel import Field, SQLModel


class InvoiceItem(SQLModel, table=True):
    __tablename__ = "invoice_item"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    quantity: int
    description: str
    price: float
