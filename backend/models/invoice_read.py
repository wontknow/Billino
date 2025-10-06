from typing import List, Optional

from sqlmodel import SQLModel


class InvoiceItemRead(SQLModel):
    id: int
    invoice_id: int
    quantity: int
    description: str
    price: float


class InvoiceRead(SQLModel):
    id: int
    number: str
    date: str
    customer_id: int
    profile_id: int
    total_amount: float
    invoice_items: List[InvoiceItemRead] = []
    include_tax: Optional[bool] = None
    tax_rate: Optional[float] = None
    is_gross_amount: bool = True

