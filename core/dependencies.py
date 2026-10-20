"""
FastAPI Authentication & Authorization Dependencies.

Uses HTTPBearer so Swagger UI provides a clean 'Paste Token' authorization dialog,
validates incoming JWT signatures, and injects the authenticated User.
"""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Header

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.security import decode_access_token
from shared.users.models import User

# HTTPBearer creates a simple, clean "Bearer Token" input box in Swagger UI
security_bearer = HTTPBearer(auto_error=False)  # <-- Crucial so it doesn't block X-API-Key requests!


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticates requests via:
    1. Human JWT Bearer Token (Authorization: Bearer <token>)
    2. Program Service API Key (X-API-Key: <secret_key>)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or missing authentication credentials.",
    )

    # -------------------------------------------------------------------
    # Option 1: Program-to-Program API Key Authentication
    # -------------------------------------------------------------------
    if x_api_key:
        cleaned_key = x_api_key.strip()

        # Look up the key in our config dictionary
        target_username = settings.SERVICE_API_KEYS.get(cleaned_key)

        if target_username:
            # Find the corresponding service user in PostgreSQL
            service_user = db.query(User).filter(User.username == target_username).first()
            if service_user:
                return service_user

        raise credentials_exception

    # -------------------------------------------------------------------
    # Option 2: Human JWT Bearer Token Authentication
    # -------------------------------------------------------------------
    if not auth:
        raise credentials_exception

    token = auth.credentials
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise credentials_exception

    return user


def require_role(*allowed_roles: str):
    """Dependency restricting endpoints to specific roles (ADMIN always allowed)."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role_str = str(current_user.role).upper()
        allowed_normalized = [r.upper() for r in allowed_roles]

        if "ADMIN" not in user_role_str and user_role_str not in allowed_normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {allowed_roles}, Your role: {current_user.role}"
            )
        return current_user

    return role_checker