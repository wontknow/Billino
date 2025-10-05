from typing import Optional

from sqlmodel import Field, SQLModel


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    address: str
    city: str
    bank_data: Optional[str] = None
    tax_number: Optional[str] = None
