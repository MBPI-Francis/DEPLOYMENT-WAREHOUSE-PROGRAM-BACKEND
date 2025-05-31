# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class SpillageAdjustmentForm(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    status_id: UUID
    qty_kg: float
    ref_number: str = Field(max_length=50, description="The reference number of the Adjustment Form")
    adjustment_date: date
    reference_date: date


    spillage_form_number: str = Field(max_length=50)
    incident_date: date
    responsible_person: str = Field(max_length=50)


class AdjustmentFormCreate(SpillageAdjustmentForm):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class AdjustmentFormUpdate(SpillageAdjustmentForm):
    pass

class AdjustmentFormResponse(BaseModel):
    id: UUID
    raw_material: str
    qty_kg: float
    ref_number: str
    wh_name: str
    status: str
    responsible_person: str
    incident_date: date
    spillage_form_number: str
    adjustment_date: date
    reference_date: date
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None

    class Config:
        from_attributes = True
