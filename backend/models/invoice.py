from typing import Optional

from sqlmodel import Field, SQLModel

class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str
    date: str
    customer_id: int = Field(foreign_key="customer.id")
    profile_id: int = Field(foreign_key="profile.id")
    total_amount: float