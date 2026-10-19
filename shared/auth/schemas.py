"""
Pydantic Schemas for Centralized Authentication.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    """Payload sent by PyQt6 or desktop login screen."""
    username: str = Field(..., description="User login username")
    password: str = Field(..., description="User plain text password")
    workstation_name: Optional[str] = Field(None, description="Client PC name on the LAN")


class TokenResponse(BaseModel):
    """Payload returned upon successful login."""
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    username: str
    full_name: str
    role: str
    department: str


class ChangePasswordRequest(BaseModel):
    """Payload for changing personal password."""
    old_password: str
    new_password: str = Field(..., min_length=4)