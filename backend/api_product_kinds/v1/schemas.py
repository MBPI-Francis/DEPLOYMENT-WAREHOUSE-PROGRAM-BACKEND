# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime

class ProductKindBase(BaseModel):
    id: str = Field(max_length=10, description="The code or id of the product kind")
    name : str = Field(min_length=3, max_length=150, description="The name of the product kind")


class ProductKindCreate(ProductKindBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    description: Optional[str] = None
    
class ProductKindUpdate(BaseModel):
    name: str = Field(min_length=3, max_length=150, description="The name of the product kind")
    description: Optional[str] = None


class ProductKindResponse(ProductKindBase):
    description: Optional[str] = None
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None


    class Config:
        from_attributes = True
