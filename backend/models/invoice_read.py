from typing import List

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
    include_tax: bool
    total_amount: float
    invoice_items: List[InvoiceItemRead] = []
