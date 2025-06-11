# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class TempHeldForm(BaseModel):
    rm_code_id: UUID
    ref_number: str
    warehouse_id: UUID
    current_status_id: UUID
    new_status_id: UUID
    change_status_date: date
    qty_kg: float


class TempHeldFormCreate(TempHeldForm):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class TempHeldFormUpdate(TempHeldForm):
    pass

class TempHeldFormResponse(BaseModel):
    id: UUID
    raw_material: str
    wh_name: str
    ref_number: str
    current_status: str
    new_status: str
    change_status_date: date
    qty_kg: float
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    date_computed: Optional[date] = None
    is_adjusted: Optional[bool] = None

    class Config:
        from_attributes = True
