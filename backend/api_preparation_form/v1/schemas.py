# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class TempPreparationForm(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    ref_number: str = Field(max_length=50, description="The reference number of the Preparation Form")
    preparation_date: date
    qty_prepared: float
    qty_return: float
    status_id: UUID

class TempPreparationFormCreate(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    ref_number: str = Field(max_length=50, description="The reference number of the Preparation Form")
    preparation_date: date
    qty_prepared: float
    qty_return: float
    status_id: UUID
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class TempPreparationFormUpdate(TempPreparationForm):
    pass

class TempPreparationFormResponse(BaseModel):
    id: UUID
    raw_material: str
    qty_prepared: float
    qty_return: float
    ref_number: str
    wh_name: str
    status: str
    preparation_date: date
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None


    class Config:
        from_attributes = True
