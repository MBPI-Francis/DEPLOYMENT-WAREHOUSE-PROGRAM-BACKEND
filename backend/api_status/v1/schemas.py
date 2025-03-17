# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

class StatusBase(BaseModel):
    name: str = Field(max_length=150, description="The name of the drop list")

class StatusCreate(StatusBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    description: Optional[str] = None

class StatusUpdate(StatusBase):
    description: Optional[str] = None


class StatusSearchResponse(BaseModel):
    id: UUID
    name: str

class StatusResponse(BaseModel):
    id: UUID
    name: str
    created_by: Optional[str] = None
    description: Optional[str] = None
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
