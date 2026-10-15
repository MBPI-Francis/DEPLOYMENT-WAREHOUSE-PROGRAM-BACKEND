"""
Pydantic Schemas for Preparation Form Module.

Provides DTOs for:
1. Traveler Integration: Worksheet lookups and atomic batch posting.
2. Ledger Maintenance CRUD: Manual deduction records using human-friendly codes
   (rm_code, wh_number, status_name) instead of database UUIDs.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    """Rounds values to exactly 2 decimal places using standard half-up commercial rounding."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ===========================================================================
# 1. Traveler Integration DTOs (Preserved as Working)
# ===========================================================================

class PrepDetailLookupItem(BaseModel):
    """Line item row returned for the PyQt6 traveler worksheet table."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    detail_id: UUID
    sequence_no: int
    rm_code: str
    rm_code_id: Optional[UUID] = None
    rm_name: Optional[str] = None
    qty_required: Decimal
    qty_prepared: Optional[Decimal] = None
    add_qty: Optional[Decimal] = Field(Decimal("0.00"))
    qty_returned: Optional[Decimal] = Field(Decimal("0.00"))
    rm_lotno: Optional[str] = Field(None, max_length=50)

    default_warehouse_id: Optional[UUID] = None
    default_wh_number: str = "1"
    default_status_id: Optional[UUID] = None
    default_status_name: str = "good"

    @field_validator("qty_required", "qty_prepared", "add_qty", "qty_returned", mode="before")
    @classmethod
    def round_quantities(cls, v):
        return _quantize_two_places(v)


class PrepLookupResponse(BaseModel):
    """Worksheet packet returned to the floor traveler screen."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    prep_form_no: Union[str, int]
    version: int
    prod_lot_no: str
    prod_id: Union[str, int]
    qty_prod: Decimal
    header_status: str
    items: List[PrepDetailLookupItem]

    @field_validator("qty_prod", mode="before")
    @classmethod
    def round_qty_prod(cls, v):
        return _quantize_two_places(v)


class PrepLineSubmission(BaseModel):
    """Floor actual line item submitted from PyQt6."""
    detail_id: UUID
    rm_code: str
    rm_code_id: Optional[UUID] = None
    rm_lot_no: str = Field(..., min_length=1, max_length=50)

    qty_required: Decimal = Field(..., ge=0)
    qty_prepared: Decimal = Field(..., ge=0)
    add_qty: Decimal = Field(Decimal("0.00"), ge=0)
    qty_returned: Decimal = Field(Decimal("0.00"), ge=0)

    warehouse_id: Optional[UUID] = None
    wh_number: Optional[str] = "1"
    status_id: Optional[UUID] = None
    status_name: Optional[str] = "good"

    @field_validator("qty_required", "qty_prepared", "add_qty", "qty_returned", mode="before")
    @classmethod
    def round_inputs(cls, v):
        return _quantize_two_places(v)


class PrepFormSubmissionRequest(BaseModel):
    """Worksheet confirmation payload submitted from PyQt6."""
    model_config = ConfigDict(coerce_numbers_to_str=True)

    prep_form_no: Union[str, int]
    prod_lot_no: str
    preparation_date: date = Field(default_factory=date.today)
    prepared_by_user_id: Optional[UUID] = None
    items: List[PrepLineSubmission] = Field(..., min_length=1)


class PrepSubmissionResponse(BaseModel):
    """Result returned after atomic posting across schema_whprep and schema_whrm."""
    success: bool
    message: str
    prep_form_no: str
    prod_lot_no: str
    deductions_recorded: int


# ===========================================================================
# 2. Ledger Maintenance DTOs (Human Codes Only - No UUIDs Required)
# ===========================================================================

class TempPreparationFormCreate(BaseModel):
    """
    Payload for manually creating a preparation deduction record.
    The client passes only unique human-friendly codes. The backend resolves the UUIDs.
    """
    ref_number: str = Field(..., max_length=50, description="Reference or Prep Form Number (e.g. 'PREP-101')")
    prod_lot_no: Optional[str] = Field(None, max_length=128, description="Production Lot Number (e.g. '0366Y-0420Y')")
    preparation_date: date = Field(default_factory=date.today, description="Transaction deduction date")

    # Pure human-readable business keys (No UUIDs!)
    rm_code: str = Field(..., min_length=1, max_length=50, description="Unique material code (e.g. 'RM-1001')")
    wh_number: str = Field("1", description="Unique warehouse number (e.g. '1' or '2')")
    status_name: str = Field("good", description="Unique quality status name (e.g. 'good', 'held : reject')")

    # Quantities & Floor Details
    qty_prepared: Decimal = Field(..., ge=0, description="Actual physical quantity issued")
    qty_return: Decimal = Field(Decimal("0.00"), ge=0, description="Quantity returned to warehouse")
    qty_required: Optional[Decimal] = Field(Decimal("0.00"), ge=0, description="Planned recipe target quantity")
    add_qty: Optional[Decimal] = Field(Decimal("0.00"), ge=0, description="Additional quantity added")
    rm_lot_no: Optional[str] = Field(None, max_length=50, description="Supplier chemical lot number")

    created_by_id: Optional[UUID] = Field(None, description="UUID of the clerk recording the entry (optional)")

    @field_validator("qty_prepared", "qty_return", "qty_required", "add_qty", mode="before")
    @classmethod
    def round_create_qtys(cls, v):
        return _quantize_two_places(v)


class TempPreparationFormUpdate(BaseModel):
    """
    Payload for modifying an existing preparation entry.
    All fields are optional; supply only what needs to be changed.
    """
    ref_number: Optional[str] = Field(None, max_length=50)
    prod_lot_no: Optional[str] = Field(None, max_length=128)
    preparation_date: Optional[date] = None

    # Optional human-readable keys for changing assigned material, warehouse, or status
    rm_code: Optional[str] = Field(None, max_length=50)
    wh_number: Optional[str] = Field(None, max_length=50)
    status_name: Optional[str] = Field(None, max_length=100)

    qty_prepared: Optional[Decimal] = Field(None, ge=0)
    qty_return: Optional[Decimal] = Field(None, ge=0)
    qty_required: Optional[Decimal] = Field(None, ge=0)
    add_qty: Optional[Decimal] = Field(None, ge=0)
    rm_lot_no: Optional[str] = Field(None, max_length=50)

    updated_by_id: Optional[UUID] = None

    @field_validator("qty_prepared", "qty_return", "qty_required", "add_qty", mode="before")
    @classmethod
    def round_update_qtys(cls, v):
        return _quantize_two_places(v)


class TempPreparationFormResponse(BaseModel):
    """Detailed response representation of an inventory deduction preparation row."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    ref_number: str
    prod_lot_no: Optional[str] = None
    raw_material: str  # rm_code
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: str
    qty_required: Decimal
    qty_prepared: Decimal
    add_qty: Decimal
    qty_return: Decimal
    rm_lot_no: Optional[str] = None
    preparation_date: date
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None
    is_cleared: Optional[bool] = None

    @field_validator("qty_prepared", "qty_return", "qty_required", "add_qty", mode="before")
    @classmethod
    def round_response_qtys(cls, v):
        return _quantize_two_places(v)