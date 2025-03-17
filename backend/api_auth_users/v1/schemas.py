# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel,Field

class AuthUserBase(BaseModel):
    user_name: str = Field(min_length=3, max_length=50, description="The user name of the user")
    password: str = Field(min_length=8, max_length=50, description="The password of the user")

class AuthUserResponse(AuthUserBase):
    pass

    class Config:
        from_attributes = True
