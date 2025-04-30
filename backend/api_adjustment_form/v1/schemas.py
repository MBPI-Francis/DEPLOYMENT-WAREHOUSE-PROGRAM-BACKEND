# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class AdjustmentForm(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    ref_number: str = Field(max_length=50, description="The reference number of the Adjustment Form")
    adjustment_date: date
    reference_date: date
    ref_form: Optional[str] = Field(max_length=50, description="The referenced document of the adjustment")
    ref_form_number: Optional[str] = Field(max_length=50, description="The referenced number of the referenced document")
    qty_kg: float
    status_id: UUID
    reason: str = Field(max_length=255, description="The reason for the adjustment")

class AdjustmentFormCreate(AdjustmentForm):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class AdjustmentFormUpdate(AdjustmentForm):
    pass

class AdjustmentFormResponse(BaseModel):
    id: UUID
    raw_material: str
    qty_kg: float
    ref_number: str
    wh_name: str
    status: str
    reason: str
    adjustment_date: date
    reference_date: date
    ref_form: Optional[str] = None
    ref_form_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None

    class Config:
        from_attributes = True
