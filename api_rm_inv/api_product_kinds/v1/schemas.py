"""
Pydantic Schemas for Product Kinds.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ProductKindBase(BaseModel):
    id: str = Field(..., max_length=10, description="The code or id of the product kind (e.g. 'MB', 'DC')")
    name: str = Field(..., min_length=3, max_length=150, description="The name of the product kind")
    description: Optional[str] = Field(None, max_length=300)


class ProductKindCreate(ProductKindBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None


class ProductKindUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, max_length=300)
    updated_by_id: Optional[UUID] = None


class ProductKindResponse(ProductKindBase):
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None