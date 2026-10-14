"""
Pydantic Schemas for Preparation Form Module.

Handles two operational workflows:
1. Floor Traveler Integration: Worksheet lookups and atomic batch posting.
2. Ledger Maintenance CRUD: Direct preparation viewing, editing, soft-deleting, and restoring.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    """Rounds quantities to exactly 2 decimal places using standard half-up rounding."""
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
# 2. Ledger CRUD DTOs (Restored & Upgraded with Human Identifiers)
# ===========================================================================

class TempPreparationFormCreate(BaseModel):
    """
    Payload for manually creating a preparation deduction record.
    Accepts human codes (rm_code, wh_number, status_name) OR internal UUIDs.
    """
    ref_number: str = Field(..., max_length=50, description="Reference or Form Number")
    prod_lot_no: Optional[str] = Field(None, max_length=128, description="Production Lot Number")
    preparation_date: date = Field(default_factory=date.today)

    # Human codes (preferred) with UUID fallbacks
    rm_code: Optional[str] = Field(None, description="Material code (e.g. 'RM-1001')")
    rm_code_id: Optional[UUID] = None

    wh_number: Optional[str] = Field("1", description="Warehouse number (e.g. '1')")
    warehouse_id: Optional[UUID] = None

    status_name: Optional[str] = Field("good", description="Quality status (e.g. 'good')")
    status_id: Optional[UUID] = None

    # Quantities
    qty_prepared: Decimal = Field(..., ge=0, description="Issued quantity")
    qty_return: Decimal = Field(Decimal("0.00"), ge=0, description="Returned quantity")
    qty_required: Optional[Decimal] = Field(Decimal("0.00"), ge=0, description="Planned recipe quantity")
    add_qty: Optional[Decimal] = Field(Decimal("0.00"), ge=0, description="Additional quantity")
    rm_lot_no: Optional[str] = Field(None, max_length=50, description="Supplier chemical lot")

    created_by_id: Optional[UUID] = None

    @field_validator("qty_prepared", "qty_return", "qty_required", "add_qty", mode="before")
    @classmethod
    def round_create_qtys(cls, v):
        return _quantize_two_places(v)


class TempPreparationFormUpdate(BaseModel):
    """
    Payload for updating an existing preparation deduction record.
    All fields are optional; supply only what requires correction.
    """
    ref_number: Optional[str] = Field(None, max_length=50)
    prod_lot_no: Optional[str] = Field(None, max_length=128)
    preparation_date: Optional[date] = None

    rm_code: Optional[str] = None
    rm_code_id: Optional[UUID] = None

    wh_number: Optional[str] = None
    warehouse_id: Optional[UUID] = None

    status_name: Optional[str] = None
    status_id: Optional[UUID] = None

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
    raw_material: str  # Human material code
    rm_name: Optional[str] = None
    wh_name: str
    wh_number: Optional[str] = None
    status: str
    qty_prepared: Decimal
    qty_return: Decimal
    qty_required: Optional[Decimal] = Decimal("0.00")
    add_qty: Optional[Decimal] = Decimal("0.00")
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