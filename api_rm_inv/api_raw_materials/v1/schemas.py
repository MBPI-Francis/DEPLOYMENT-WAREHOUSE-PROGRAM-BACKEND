"""
Pydantic Schemas for Raw Materials.

Defines input validation, payload serialization, and OpenAPI response shapes
for single-item transactions and bulk operations.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class RawMaterialBase(BaseModel):
    """Common properties shared across raw material payloads."""
    rm_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Unique item code representing the raw material (e.g., 'RM-1001')"
    )
    rm_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Descriptive item name (e.g., 'Titanium White Pigment')"
    )
    description: Optional[str] = Field(
        None,
        max_length=300,
        description="Additional technical details or storage notes"
    )


class RawMaterialCreate(RawMaterialBase):
    """Payload schema used when registering a brand-new material."""
    type: Optional[str] = Field(
        "RM",
        description="Classification: 'RM' for raw material or 'SUPPLY' for general supplies"
    )
    created_by_id: Optional[UUID] = Field(
        None,
        description="UUID of the user registering this item"
    )


class RawMaterialUpdate(BaseModel):
    """
    Payload schema for updating an existing material.
    All fields are optional—client programs only send what needs to change.
    """
    new_rm_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="Fill this ONLY if you need to rename/correct the material code"
    )
    rm_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Updated friendly material name"
    )
    description: Optional[str] = Field(
        None,
        max_length=300,
        description="Updated technical notes"
    )
    type: Optional[str] = Field(
        None,
        description="Updated classification: 'RM' or 'SUPPLY'"
    )
    updated_by_id: Optional[UUID] = Field(
        None,
        description="UUID of the user making this update"
    )


class RawMaterialResponse(BaseModel):
    """Standard API response representation for a single raw material item."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rm_code: str
    rm_name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class TransformedRawMaterialResponse(BaseModel):
    """Summary view formatting material data along with the creator's full name."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rm_code: str
    rm_name: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    """Generic status response for operations like delete and restore."""
    message: str
    rm_code: str