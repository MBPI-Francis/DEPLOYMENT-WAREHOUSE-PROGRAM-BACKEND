# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime


class TempReceivingReport(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    status_id: UUID
    ref_number: str = Field(max_length=50, description="The reference number of the Receiving Report")
    receiving_date: date
    qty_kg: float

class TempReceivingReportCreate(TempReceivingReport):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class TempReceivingReportUpdate(TempReceivingReport):
    pass

class TempReceivingReportResponse(BaseModel):
    id: UUID
    raw_material: str
    qty_kg: float
    ref_number: str
    wh_name: str
    status: str
    receiving_date: date
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None

    class Config:
        from_attributes = True
