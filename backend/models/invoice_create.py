import re
from typing import List, Optional

from pydantic import model_validator
from sqlmodel import SQLModel


class InvoiceItemCreate(SQLModel):
    quantity: int
    description: str
    price: float
    tax_rate: Optional[float] = None


class InvoiceCreateWithNumber(SQLModel):
    """Invoice creation model WITH manual number (for backward compatibility)"""
    number: str
    date: str
    customer_id: int
    profile_id: int
    total_amount: float
    invoice_items: List[InvoiceItemCreate]
    include_tax: Optional[bool] = None
    tax_rate: Optional[float] = None
    is_gross_amount: bool = False

    @model_validator(mode="after")
    def validate_invoice_with_number(self):
        if self.is_gross_amount and not self.include_tax:
            raise ValueError("is_gross_amount can only be True if include_tax is True.")

        if self.is_gross_amount and self.tax_rate is None:
            raise ValueError("tax_rate must be provided if is_gross_amount is True.")

        if not self.invoice_items or len(self.invoice_items) == 0:
            raise ValueError("Invoice must have at least one item.")
        if self.total_amount < 0:
            raise ValueError("total_amount must be non-negative.")

        if self.include_tax is False and self.tax_rate not in (None, 0, 0.0):
            raise ValueError("tax_rate must be 0 if include_tax is False.")

        if self.include_tax is True:
            if self.tax_rate is None:
                raise ValueError("tax_rate must be provided if include_tax is True.")
            if self.tax_rate < 0 or self.tax_rate > 1:
                raise ValueError("tax_rate must be between 0 and 1.")

        # Validate number format: "YY | NNN" (e.g., "25 | 001")
        if not re.match(r"^\d{2} \| \d{3,}$", self.number):
            raise ValueError(
                "Invoice number must follow format 'YY | NNN' (e.g., '25 | 001'). "
                "Two digits, space, pipe, space, at least three digits."
            )

        return self


class InvoiceCreate(SQLModel):
    """Invoice creation model WITHOUT number (auto-generated)"""
    date: str
    customer_id: int
    profile_id: int
    total_amount: float
    invoice_items: List[InvoiceItemCreate]
    include_tax: Optional[bool] = None
    tax_rate: Optional[float] = None
    is_gross_amount: bool = False

    @model_validator(mode="after")
    def validate_invoice(self):
        if self.is_gross_amount and not self.include_tax:
            raise ValueError("is_gross_amount can only be True if include_tax is True.")

        if self.is_gross_amount and self.tax_rate is None:
            raise ValueError("tax_rate must be provided if is_gross_amount is True.")

        if not self.invoice_items or len(self.invoice_items) == 0:
            raise ValueError("Invoice must have at least one item.")
        if self.total_amount < 0:
            raise ValueError("total_amount must be non-negative.")

        if self.include_tax is False and self.tax_rate not in (None, 0, 0.0):
            raise ValueError("tax_rate must be 0 if include_tax is False.")

        if self.include_tax is True:
            if self.tax_rate is None:
                raise ValueError("tax_rate must be provided if include_tax is True.")
            if self.tax_rate < 0 or self.tax_rate > 1:
                raise ValueError("tax_rate must be between 0 and 1.")

        return self
