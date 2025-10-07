from typing import List, Optional

from sqlmodel import SQLModel


class InvoiceItemCreate(SQLModel):
    quantity: int
    description: str
    price: float
    tax_rate: Optional[float] = None


class InvoiceCreate(SQLModel):
    number: str
    date: str
    customer_id: int
    profile_id: int
    total_amount: float
    invoice_items: List[InvoiceItemCreate]
    include_tax: Optional[bool] = None
    tax_rate: Optional[float] = None
    is_gross_amount: bool = True
