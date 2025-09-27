from typing import Optional

from sqlmodel import Field, SQLModel


class Invoice_Item(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id")
    quantity: int
    description: str
    price: float
