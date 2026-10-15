"""
Pydantic Schemas for Transfer Forms.

Provides input validation and serialization for warehouse transfers using
human-readable business keys (rm_code, from_wh_number, to_wh_number, status_name).
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


class TempTransferFormCreate(BaseModel):
    """
    Payload for recording a warehouse-to-warehouse stock transfer.
    No UUIDs required: the client supplies only unique human business keys.
    """
    ref_number: str = Field(..., max_length=50, description="Transfer Slip Number (e.g., 'TF-2026-001')")
    transfer_date: date = Field(default_factory=date.today, description="Date physical stock was relocated")

    # Human-readable business keys
    rm_code: str = Field(..., min_length=1, max_length=50, description="Material code being transferred (e.g. 'RM-1001')")
    from_wh_number: str = Field(..., description="Origin warehouse number (e.g. '1')")
    to_wh_number: str = Field(..., description="Destination warehouse number (e.g. '2')")
    status_name: Optional[str] = Field("good", description="Quality status category (e.g. 'good', 'held : under evaluation')")

    qty_kg: Decimal = Field(..., gt=0, description="Net weight transferred in kilograms")
    created_by_id: Optional[UUID] = Field(None, description="UUID of the warehouse clerk")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class TempTransferFormUpdate(BaseModel):
    """
    Payload for correcting an existing transfer record.
    All fields are optional; supply only what requires correction.
    """
    ref_number: Optional[str] = Field(None, max_length=50)
    transfer_date: Optional[date] = None
    rm_code: Optional[str] = Field(None, max_length=50)
    from_wh_number: Optional[str] = Field(None, max_length=50)
    to_wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)
    updated_by_id: Optional[UUID] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class TempTransferFormResponse(BaseModel):
    """Response representation of a transfer record formatted for PyQt6 table models."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    transfer_date: date
    raw_material: str  # rm_code
    from_warehouse: str  # wh_name of source
    to_warehouse: str    # wh_name of destination
    qty_kg: Decimal
    status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)