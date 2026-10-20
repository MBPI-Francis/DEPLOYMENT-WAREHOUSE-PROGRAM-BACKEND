"""
Pydantic Schemas for Warehouses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class WarehouseBase(BaseModel):
    """Common properties shared across warehouse payloads."""
    wh_number: int = Field(..., description="Facility number (smallint, e.g. 1, 2, 4)")
    wh_name: str = Field(..., max_length=150, description="Readable name of the warehouse")
    description: Optional[str] = Field(None, max_length=300)


class WarehouseCreate(WarehouseBase):
    """Payload schema for creating a new warehouse."""
    created_by_id: Optional[UUID] = None


class WarehouseUpdate(BaseModel):
    """Payload schema for updating an existing warehouse."""
    new_wh_number: Optional[int] = Field(None, description="Use this ONLY if renaming warehouse number")
    wh_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=300)
    updated_by_id: Optional[UUID] = None


class WarehouseResponse(BaseModel):
    """Standard API response representation for a single warehouse."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    wh_number: int
    wh_name: str
    description: Optional[str] = None


class TransformedWarehouseResponse(BaseModel):
    """Summary view formatting warehouse data with creator audit details."""
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    id: UUID
    wh_number: int
    wh_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic status response for operations like delete and restore."""
    message: str
    wh_number: int