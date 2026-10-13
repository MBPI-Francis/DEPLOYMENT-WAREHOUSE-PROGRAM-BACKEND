# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime, date

class NotesBase(BaseModel):
    product_code: str = Field(max_length=80, description="The product code of the notes record")
    lot_number: str = Field(None, max_length=80, description="The lot number of the notes record")
    product_kind_id: str = Field(None, max_length=10, description="The product kind of the notes record")
    stock_change_date: date

class NotesCreate(NotesBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class NotesUpdate(NotesBase):
    pass

class NotesResponse(BaseModel):
    id: UUID
    product_code: str
    lot_number: str
    product_kind_id: str
    stock_change_date: date
    created_at: datetime
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    date_computed: Optional[date] = None
    updated_at: datetime

    class Config:
        from_attributes = True
