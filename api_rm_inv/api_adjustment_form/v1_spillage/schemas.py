"""
Pydantic Schemas for Spillage Adjustment Forms.

Provides input validation and serialization for spillage losses using
human-readable business keys (rm_code, wh_number, status_name).
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Union[Decimal, float, int, str]]) -> Optional[Decimal]:
    """
    Rounds values to exactly 2 decimal places using half-up commercial rounding.
    Safely handles leading '+' or '-' signs (e.g., '+20.00', '-21.50', '20').
    """
    if value is None:
        return None
    # Strips whitespace; Python's Decimal cleanly parses both '+20.00' and '-20.00'
    cleaned = str(value).strip()
    return Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class AdjustmentFormCreate(BaseModel):
    """
    Payload for creating a Spillage Adjustment Form entry.
    No UUIDs required: client programs supply human business keys.
    """
    ref_number: str = Field(..., max_length=50, description="Ledger Reference Number (e.g. 'ADJ-2026-001')")
    spillage_form_number: str = Field(..., max_length=50, description="Physical Incident Form Number (e.g. 'SPF-0092')")
    adjustment_date: date = Field(default_factory=date.today, description="Ledger posting date")
    reference_date: date = Field(default_factory=date.today, description="Reference document date")
    incident_date: date = Field(default_factory=date.today, description="Date physical spillage occurred")

    # Human-readable identifiers
    rm_code: str = Field(..., min_length=1, max_length=50, description="Material code spilled (e.g. 'K907')")
    wh_number: str = Field("1", description="Warehouse where spillage occurred (e.g. '1')")
    status_name: str = Field("good", description="Quality status of spilled material (e.g. 'good', 'held : contaminated')")

    qty_kg: Decimal = Field(...,
                            description="Quantity in kilograms (can be negative for reversals or credit adjustments)")
    responsible_person: str = Field(..., max_length=100, description="Employee or supervisor responsible")
    reason: str = Field(..., max_length=255, description="Cause of spillage (e.g. 'Forklift puncture', 'Bag tear')")

    created_by_id: Optional[UUID] = Field(None, description="UUID of recording clerk")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class AdjustmentFormUpdate(BaseModel):
    """Payload for modifying an existing spillage record."""
    ref_number: Optional[str] = Field(None, max_length=50)
    spillage_form_number: Optional[str] = Field(None, max_length=50)
    adjustment_date: Optional[date] = None
    reference_date: Optional[date] = None
    incident_date: Optional[date] = None

    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)

    qty_kg: Optional[Decimal] = Field(None, description="Updated quantity in kilograms (positive or negative)")
    responsible_person: Optional[str] = Field(None, max_length=100)
    reason: Optional[str] = Field(None, max_length=255)
    updated_by_id: Optional[UUID] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class AdjustmentFormResponse(BaseModel):
    """Response DTO formatted for the PyQt6 desktop table model."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    spillage_form_number: str
    adjustment_date: date
    reference_date: date
    incident_date: date
    raw_material: str  # rm_code
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: str
    qty_kg: Decimal
    responsible_person: str
    reason: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)