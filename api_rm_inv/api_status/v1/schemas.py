"""
Pydantic Schemas for Status Module.
"""

from datetime import datetime
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class StatusBase(BaseModel):
    name: str = Field(..., max_length=150, description="The name of the status classification")
    description: Optional[str] = Field(None, max_length=300)


class StatusCreate(StatusBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None


class StatusUpdate(BaseModel):
    new_name: Optional[str] = Field(None, max_length=150, description="Use this ONLY if renaming status name")
    description: Optional[str] = Field(None, max_length=300)
    updated_by_id: Optional[UUID] = None


class StatusSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)
    id: UUID
    name: str


class StatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None


class TransformedStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None