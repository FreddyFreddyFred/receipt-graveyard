"""Pydantic models for receipt line items and extracted receipts."""

from datetime import date as Date
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A receipt item with nullable amounts for partial OCR results."""

    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    category: str | None = None


class Receipt(BaseModel):
    """Structured receipt data; OCR-derived fields may be unavailable."""

    id: UUID = Field(default_factory=uuid4)
    employee_id: str | None = None
    vendor: str | None = None
    date: Date | None = None
    total: Decimal | None = None
    currency: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    tax: Decimal | None = None
    tip: Decimal | None = None
