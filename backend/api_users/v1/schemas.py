# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel,Field
from uuid import UUID
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    user_name: str = Field(min_length=3, max_length=150, description="The user name of the user")
    first_name: str = Field(min_length=3, max_length=50, description="The first name of the user")
    last_name: str = Field(min_length=3, max_length=50, description="The last name of the user")
    password: str = Field(min_length=8, max_length=50, description="The password of the user")
    is_superuser: bool
    is_reguser: bool
    department_id: Optional[UUID] = None


class UserCreate(UserBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None

class UserUpdate(UserBase):
    pass
class UserResponse(UserBase):
    pass

    class Config:
        from_attributes = True
