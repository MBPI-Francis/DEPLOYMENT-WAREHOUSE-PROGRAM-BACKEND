"""
Pydantic Schemas for Form Entries Adjustment Module.

Provides specialized, dedicated request schemas for each transaction type:
- ReceivingAdjustmentCreate
- OutgoingAdjustmentCreate
- PreparationAdjustmentCreate
- TransferAdjustmentCreate
- ChangeStatusAdjustmentCreate
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


# ===========================================================================
# Base Header (Common to all adjustments)
# ===========================================================================

class AdjustmentHeaderBase(BaseModel):
    """Common metadata required for any form correction."""
    ref_number: str = Field(..., max_length=50, description="Adjustment Reference Slip Number (e.g. 'ADJ-2026-001')")
    adjustment_date: date = Field(default_factory=date.today, description="Date adjustment is recorded")
    referenced_date: date = Field(default_factory=date.today, description="Date of original incorrect transaction")
    adjustment_type: str = Field(..., max_length=50, description="Reason category (e.g. 'System Entry Error', 'Form Correction')")
    responsible_person: Optional[str] = Field(None, max_length=100, description="Person authorizing the adjustment")
    created_by_id: Optional[UUID] = None


# ===========================================================================
# Dedicated Creation Schemas (Clean & Form-Specific)
# ===========================================================================

class ReceivingAdjustmentCreate(AdjustmentHeaderBase):
    """Payload strictly for correcting an incorrect Receiving Report."""
    incorrect_receiving_id: UUID = Field(..., description="UUID of the original incorrect receiving report")
    rm_code: str = Field(..., min_length=1, max_length=50, description="Correct material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Correct warehouse number (e.g. '1')")
    status_name: str = Field("good", description="Correct quality status (e.g. 'good')")
    qty_kg: Decimal = Field(..., gt=0, description="Correct net weight in kilograms")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class OutgoingAdjustmentCreate(AdjustmentHeaderBase):
    """Payload strictly for correcting an incorrect Outgoing Report."""
    incorrect_outgoing_id: UUID = Field(..., description="UUID of the original incorrect outgoing report")
    rm_code: str = Field(..., min_length=1, max_length=50, description="Correct material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Correct warehouse number (e.g. '1')")
    status_name: str = Field("good", description="Correct quality status (e.g. 'good')")
    qty_kg: Decimal = Field(..., gt=0, description="Correct net weight in kilograms")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class PreparationAdjustmentCreate(AdjustmentHeaderBase):
    """Payload strictly for correcting an incorrect Preparation Form."""
    incorrect_preparation_id: UUID = Field(..., description="UUID of the original incorrect preparation form")
    rm_code: str = Field(..., min_length=1, max_length=50, description="Correct material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Correct warehouse number (e.g. '1')")
    status_name: str = Field("good", description="Correct quality status (e.g. 'good')")
    qty_prepared: Decimal = Field(..., ge=0, description="Correct quantity prepared/issued")
    qty_return: Decimal = Field(Decimal("0.00"), ge=0, description="Correct quantity returned")

    @field_validator("qty_prepared", "qty_return", mode="before")
    @classmethod
    def round_prep_quantities(cls, v):
        return _quantize_two_places(v)


class TransferAdjustmentCreate(AdjustmentHeaderBase):
    """Payload strictly for correcting an incorrect Transfer Form."""
    incorrect_transfer_id: UUID = Field(..., description="UUID of the original incorrect transfer form")
    rm_code: str = Field(..., min_length=1, max_length=50, description="Correct material code (e.g. 'RM-1001')")
    from_wh_number: str = Field(..., description="Correct origin warehouse number (e.g. '1')")
    to_wh_number: str = Field(..., description="Correct destination warehouse number (e.g. '2')")
    status_name: str = Field("good", description="Correct quality status (e.g. 'good')")
    qty_kg: Decimal = Field(..., gt=0, description="Correct net weight transferred in kilograms")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class ChangeStatusAdjustmentCreate(AdjustmentHeaderBase):
    """Payload strictly for correcting an incorrect Change Status Form."""
    incorrect_change_status_id: UUID = Field(..., description="UUID of the original incorrect status change form")
    rm_code: str = Field(..., min_length=1, max_length=50, description="Correct material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Correct warehouse location number (e.g. '1')")
    current_status_name: str = Field(..., description="Correct origin status (e.g. 'held : contaminated')")
    new_status_name: str = Field(..., description="Correct target status (e.g. 'good')")
    qty_kg: Decimal = Field(..., gt=0, description="Correct net weight reclassified in kilograms")

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


# ===========================================================================
# Update & Response Schemas
# ===========================================================================

class AdjustmentHeaderUpdate(BaseModel):
    """Optional header metadata that can be changed during an update."""
    ref_number: Optional[str] = Field(None, max_length=50)
    adjustment_date: Optional[date] = None
    referenced_date: Optional[date] = None
    adjustment_type: Optional[str] = Field(None, max_length=50)
    responsible_person: Optional[str] = Field(None, max_length=100)
    updated_by_id: Optional[UUID] = None


class ReceivingAdjustmentUpdate(AdjustmentHeaderUpdate):
    """Payload for updating a Receiving Report correction."""
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class OutgoingAdjustmentUpdate(AdjustmentHeaderUpdate):
    """Payload for updating an Outgoing Report correction."""
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class PreparationAdjustmentUpdate(AdjustmentHeaderUpdate):
    """Payload for updating a Preparation Form correction."""
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_prepared: Optional[Decimal] = Field(None, ge=0)
    qty_return: Optional[Decimal] = Field(None, ge=0)

    @field_validator("qty_prepared", "qty_return", mode="before")
    @classmethod
    def round_prep_quantities(cls, v):
        return _quantize_two_places(v)


class TransferAdjustmentUpdate(AdjustmentHeaderUpdate):
    """Payload for updating a Transfer Form correction."""
    rm_code: Optional[str] = Field(None, max_length=50)
    from_wh_number: Optional[str] = Field(None, max_length=50)
    to_wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class ChangeStatusAdjustmentUpdate(AdjustmentHeaderUpdate):
    """Payload for updating a Change Status Form correction."""
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    current_status_name: Optional[str] = Field(None, max_length=100)
    new_status_name: Optional[str] = Field(None, max_length=100)
    qty_kg: Optional[Decimal] = Field(None, gt=0)

    @field_validator("qty_kg", mode="before")
    @classmethod
    def round_weight(cls, v):
        return _quantize_two_places(v)


class AdjustmentFormResponse(BaseModel):
    """Response representation formatted for PyQt6 table display."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    adjustment_parent_id: UUID
    ref_number: str
    adjustment_type: str
    responsible_person: Optional[str] = None
    adjustment_date: date
    referenced_date: date

    raw_material: str  # rm_code
    rm_name: Optional[str] = None
    qty_kg: Optional[Decimal] = None
    qty_prepared: Optional[Decimal] = None
    qty_return: Optional[Decimal] = None

    wh_name: Optional[str] = None
    wh_number: Optional[str] = None
    from_warehouse: Optional[str] = None
    to_warehouse: Optional[str] = None

    status: Optional[str] = None
    current_status: Optional[str] = None
    new_status: Optional[str] = None

    incorrect_receiving_id: Optional[UUID] = None
    incorrect_outgoing_id: Optional[UUID] = None
    incorrect_preparation_id: Optional[UUID] = None
    incorrect_transfer_id: Optional[UUID] = None
    incorrect_change_status_id: Optional[UUID] = None

    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None

    @field_validator("qty_kg", "qty_prepared", "qty_return", mode="before")
    @classmethod
    def round_response_quantities(cls, v):
        return _quantize_two_places(v)