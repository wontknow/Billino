from typing import Optional

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    bank_data: Optional[str] = None
    tax_number: Optional[str] = None
    include_tax: bool = Field(
        default=True, description="Ob Umsatzsteuer ausgewiesen wird (§19 UStG)"
    )
    default_tax_rate: float = Field(
        default=0.19, description="Standard-Steuersatz (z. B. 0.19 oder 0.07)"
    )
