"""
FastAPI Authentication & Authorization Dependencies.

Uses HTTPBearer so Swagger UI provides a clean 'Paste Token' authorization dialog,
validates incoming JWT signatures, and injects the authenticated User.
"""

from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import decode_access_token
from shared.users.models import User

# HTTPBearer creates a simple, clean "Bearer Token" input box in Swagger UI
security_bearer = HTTPBearer()


def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Extracts the Bearer token from the HTTP Authorization header,
    verifies its cryptographic signature, and returns the User from PostgreSQL.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # auth.credentials contains the raw token string
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