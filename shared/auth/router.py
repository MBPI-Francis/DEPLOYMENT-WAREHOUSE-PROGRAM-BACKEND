"""
API Router for Centralized Authentication.

Endpoints:
- POST /api/v1/auth/login: Issues 12-hour JWT token.
- GET /api/v1/auth/me: Returns logged-in profile.
- POST /api/v1/auth/change-password: Password updates.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from shared.auth.schemas import LoginRequest, TokenResponse, ChangePasswordRequest
from shared.auth.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication (Centralized)"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login to obtain a 12-hour session JWT token"
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates against tbl_users and returns a signed offline JWT token."""
    service = AuthService(db)
    return service.login(payload)


@router.get(
    "/me",
    summary="Get current logged-in user profile"
)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile and role permissions of the authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": str(current_user.role),
        "department": str(current_user.department),
        "workstation_name": current_user.workstation_name
    }


@router.post(
    "/change-password",
    summary="Change user password"
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates password for the authenticated user."""
    service = AuthService(db)
    return service.change_password(current_user, payload)