"""
Pydantic Schemas for Stock on Hand Module.

Provides validation, serialization, and 2-decimal commercial rounding
for inventory balance records and historical recalculation snapshots.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    """Rounds values to exactly 2 decimal places using half-up commercial rounding."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class StockOnHandCreate(BaseModel):
    """
    Payload for creating an initial Stock on Hand baseline row.
    Accepts human business keys directly (rm_code, wh_number, status_name).
    """
    rm_code: str = Field(..., min_length=1, max_length=50, description="Raw material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Warehouse number (e.g. '1')")
    status_name: str = Field("good", description="Quality status name (e.g. 'good', 'held : reject')")

    rm_soh: Decimal = Field(..., description="Initial stock quantity on hand in kilograms")
    stock_recalculation_count: Optional[int] = Field(None, description="Generation count (defaults to latest + 1)")
    description: Optional[str] = Field(None, max_length=300, description="Notes on balance initialization")
    created_by_id: Optional[UUID] = None

    @field_validator("rm_soh", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class StockOnHandUpdate(BaseModel):
    """Payload for modifying an SOH entry directly."""
    rm_soh: Optional[Decimal] = Field(None, description="Corrected baseline quantity")
    description: Optional[str] = Field(None, max_length=300)
    updated_by_id: Optional[UUID] = None

    @field_validator("rm_soh", mode="before")
    @classmethod
    def round_update_weight(cls, v):
        return _quantize_two_places(v)


class StockOnHandResponse(BaseModel):
    """Response DTO for standard SOH record representations."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    rm_code: str
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: Optional[str] = None
    rm_soh: Decimal
    stock_recalculation_count: int
    stock_change_date: datetime
    date_computed: Optional[date] = None
    description: Optional[str] = None


    @field_validator("rm_soh", mode="before")
    @classmethod
    def round_response_weight(cls, v):
        return _quantize_two_places(v)


class HistoricalStockOnHandResponse(BaseModel):
    """Response DTO formatted for the historical recalculation balance grid in PyQt6."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    wh_id: UUID
    wh_name: str
    wh_number: Optional[str] = None
    rm_id: UUID
    rm_code: str
    qty: Decimal
    stock_change_date: Optional[datetime] = None
    status_name: Optional[str] = None
    status_id: Optional[UUID] = None
    date_computed: Optional[date] = None

    @field_validator("qty", mode="before")
    @classmethod
    def round_qty(cls, v):
        return _quantize_two_places(v)