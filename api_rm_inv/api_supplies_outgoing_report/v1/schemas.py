"""
Pydantic Schemas for Supplies Outgoing Reports.

Enforces pure human business keys (rm_code, wh_number, status_name).
Zero client-supplied UUIDs required.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SuppliesOutgoingFormCreate(BaseModel):
    """
    Client submission schema.
    Barcode scanners and clerks only send natural business keys.
    """
    rm_code: str = Field(..., min_length=2, max_length=50, description="Supply item code (e.g. 'SUP-101')")
    wh_number: str = Field(..., description="Warehouse facility number (e.g. '1' or '2')")
    status_name: str = Field(default="good", description="Quality status (e.g. 'good', 'held')")
    ref_number: str = Field(..., max_length=50, description="Tracking reference or dispatch slip number")
    outgoing_date: date = Field(default_factory=date.today, description="Physical dispatch date")
    qty_kg: Decimal = Field(..., gt=0, description="Dispatch quantity (must be greater than 0.00)")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class SuppliesOutgoingFormUpdate(BaseModel):
    """Update schema. All fields optional; purely human keys."""
    rm_code: Optional[str] = Field(None, description="Updated supply code")
    wh_number: Optional[str] = Field(None, description="Updated warehouse number")
    status_name: Optional[str] = Field(None, description="Updated quality status")
    ref_number: Optional[str] = Field(None, max_length=50)
    outgoing_date: Optional[date] = None
    qty_kg: Optional[Decimal] = Field(None, gt=0)

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class SuppliesOutgoingFormResponse(BaseModel):
    """Standard API response representation for desktop table models."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    outgoing_date: date
    qty_kg: Decimal
    raw_material: str
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)