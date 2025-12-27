from typing import List, Optional

from sqlmodel import SQLModel


class InvoiceItemRead(SQLModel):
    id: int
    invoice_id: int
    quantity: int
    description: str
    price: float
    tax_rate: Optional[float] = None


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
    # Computed fields for frontend consumption (backend is source of truth)
    total_net: Optional[float] = None
    total_tax: Optional[float] = None
    total_gross: Optional[float] = None
    customer_name: Optional[str] = None
