# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class TempTransferForm(BaseModel):
    rm_code_id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    status_id: Optional[UUID] = None
    ref_number: str = Field(max_length=50, description="The reference number of the Transfer Form")
    transfer_date: date
    qty_kg: float

class TempTransferFormCreate(TempTransferForm):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class TempTransferFormUpdate(TempTransferForm):
    pass

class TempTransferFormResponse(BaseModel):
    id: UUID
    raw_material: str
    from_warehouse: str
    to_warehouse: str
    ref_number: str
    transfer_date: date
    qty_kg: float
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None

    class Config:
        from_attributes = True
