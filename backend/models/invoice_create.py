from typing import List

from sqlmodel import SQLModel


class InvoiceItemCreate(SQLModel):
    quantity: int
    description: str
    price: float


class InvoiceCreate(SQLModel):
    number: str
    date: str
    customer_id: int
    profile_id: int
    include_tax: bool 
    total_amount: float
    invoice_items: List[InvoiceItemCreate]
