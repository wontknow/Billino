from typing import Optional
from sqlmodel import Field, SQLModel


class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: str
    date: str
    customer_id: int = Field(foreign_key="customer.id")
    profile_id: int = Field(foreign_key="profile.id")
    total_amount: float
    include_tax: Optional[bool] = Field(default=None, description="Überschreibt Profile.include_tax, falls gesetzt")
    tax_rate: Optional[float] = Field(default=None, description="Individueller Steuersatz, falls abweichend vom Profil")
    is_gross_amount: bool = Field(default=True, description="True, wenn total_amount Bruttobetrag ist")
