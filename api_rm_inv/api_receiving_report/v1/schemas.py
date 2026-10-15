"""
Pydantic Schemas for Receiving Reports.

Accepts human-friendly business keys (rm_code, wh_number, status_name)
and standardizes all incoming weights to 2 decimal places.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    """Rounds values to exactly 2 decimal places using half-up commercial rounding."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TempReceivingReportCreate(BaseModel):
    """
    Payload for creating an inbound receiving report.
    No UUIDs required: the client supplies only unique human business keys.
    """
    ref_number: str = Field(..., max_length=50, description="RR Number or Supplier Delivery Receipt (DR) number")
    receiving_date: date = Field(default_factory=date.today, description="Date shipment was physically received")

    # Human-readable identifiers
    rm_code: str = Field(..., min_length=1, max_length=50, description="Raw material catalog code (e.g., 'RM-1001')")
    wh_number: str = Field("1", description="Target destination warehouse number (e.g., '1')")
    status_name: str = Field("good", description="Quality inspection status (e.g., 'good', 'held : under evaluation')")

    qty_kg: Decimal = Field(..., gt=0, description="Net weight received in kilograms (rounded to 2 decimal places)")
    created_by_id: Optional[UUID] = Field(None, description="UUID of the receiving clerk")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class TempReceivingReportUpdate(BaseModel):
    """
    Payload for modifying an existing receiving report.
    All fields are optional; supply only what needs correction.
    """
    ref_number: Optional[str] = Field(None, max_length=50)
    receiving_date: Optional[date] = None
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)
    updated_by_id: Optional[UUID] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class TempReceivingReportResponse(BaseModel):
    """API response DTO formatted for the PyQt6 desktop table model."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    receiving_date: date
    qty_kg: Decimal
    raw_material: str  # rm_code
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