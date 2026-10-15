"""
Pydantic Schemas for Status Change (Held Form) Module.

Provides validation and serialization for quality reclassification transactions
using human business keys (rm_code, wh_number, current_status_name, new_status_name).
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


class TempHeldFormCreate(BaseModel):
    """
    Payload for creating a Quality Status Change entry.
    All foreign keys are supplied via human-readable business strings.
    """
    ref_number: str = Field(..., max_length=50, description="Inspection / Held Report Reference Number (e.g. 'HF-2026-001')")
    change_status_date: date = Field(default_factory=date.today, description="Date quality reclassification took place")

    # Human-readable identifiers
    rm_code: str = Field(..., min_length=1, max_length=50, description="Material code being reclassified (e.g. 'K907')")
    wh_number: str = Field("1", description="Warehouse location number (e.g. '1')")
    current_status_name: str = Field(..., description="Current quality status (e.g. 'held : contaminated')")
    new_status_name: str = Field(..., description="New target quality status (e.g. 'good')")

    qty_kg: Decimal = Field(..., gt=0, description="Quantity in kilograms to reclassify")
    created_by_id: Optional[UUID] = Field(None, description="UUID of user initiating change")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class TempHeldFormUpdate(BaseModel):
    """Payload for modifying an existing status change record."""
    ref_number: Optional[str] = Field(None, max_length=50)
    change_status_date: Optional[date] = None
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    current_status_name: Optional[str] = Field(None, max_length=100)
    new_status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)
    updated_by_id: Optional[UUID] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class TempHeldFormResponse(BaseModel):
    """Response DTO formatted for the PyQt6 desktop table model."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    change_status_date: date
    raw_material: str  # rm_code
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    current_status: str
    new_status: str
    qty_kg: Decimal
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)