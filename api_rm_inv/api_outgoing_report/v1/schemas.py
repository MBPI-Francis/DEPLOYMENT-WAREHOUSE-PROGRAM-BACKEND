"""
Pydantic Schemas for Outgoing Reports (v2).

Accepts human business keys (rm_code, wh_number, status_name) and
standardizes all outbound quantities to 2 decimal places.
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


class OutgoingFormCreate(BaseModel):
    """
    Payload for creating an outbound dispatch report.
    No UUIDs required: client programs supply human business keys.
    """
    ref_number: str = Field(..., max_length=50, description="Gate Pass, Delivery Receipt (DR), or Outgoing Slip number")
    outgoing_date: date = Field(default_factory=date.today, description="Physical dispatch date")

    # Human-readable identifiers
    rm_code: str = Field(..., min_length=1, max_length=50, description="Material code being dispatched (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Origin warehouse number (e.g. '1')")
    status_name: str = Field("good", description="Quality status category (e.g. 'good', 'held : reject')")

    qty_kg: Decimal = Field(..., gt=0, description="Quantity dispatched in kilograms")
    outgoing_type: str = Field("RM", description="Classification: 'RM' for raw material or 'SUPPLY' for warehouse supplies")
    outgoing_destination: Optional[str] = Field(None, max_length=200, description="Recipient, customer, toller, or disposal facility")

    created_by_id: Optional[UUID] = Field(None, description="UUID of user authorizing the dispatch")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class OutgoingFormUpdate(BaseModel):
    """Payload for modifying an existing outgoing report."""
    ref_number: Optional[str] = Field(None, max_length=50)
    outgoing_date: Optional[date] = None
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)
    outgoing_type: Optional[str] = Field(None, max_length=50)
    outgoing_destination: Optional[str] = Field(None, max_length=200)
    updated_by_id: Optional[UUID] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class OutgoingFormResponse(BaseModel):
    """API response DTO formatted for the PyQt6 desktop table model."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    outgoing_date: date
    qty_kg: Decimal
    raw_material: str  # rm_code
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: str
    outgoing_type: str
    outgoing_destination: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)