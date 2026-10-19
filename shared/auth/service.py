"""
Authentication Service Layer with Automated Audit Logging.

Verifies credentials, records login audit events (success/failure)
in schema_whrm.tbl_auth_logs, and issues 12-hour session tokens.
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.security import verify_password, hash_password, create_access_token
from shared.users.models import User
from shared.auth.schemas import LoginRequest, TokenResponse, ChangePasswordRequest


class AuthService:
    """Service handling credential verification, tokens, and audit trail logging."""

    def __init__(self, db: Session):
        self.db = db

    def _log_auth_event(
        self,
        username: str,
        status_msg: str,
        client_ip: str,
        workstation: Optional[str] = None
    ) -> None:
        """
        Records login attempts into schema_whrm.tbl_auth_logs for audit tracking.
        Fails silently to ensure audit logging never crashes the login flow.
        """
        try:
            log_sql = text("""
                INSERT INTO schema_whrm.tbl_auth_logs 
                    (username, status, ip_address, workstation_name, created_at)
                VALUES 
                    (:username, :status, :ip, :workstation, NOW())
            """)
            self.db.execute(log_sql, {
                "username": username,
                "status": status_msg,
                "ip": client_ip,
                "workstation": workstation
            })
            self.db.commit()
        except Exception:
            # If tbl_auth_logs has different column names or constraints, rollback safely
            self.db.rollback()

    def login(self, payload: LoginRequest, client_ip: str = "127.0.0.1") -> TokenResponse:
        """Authenticates user credentials and issues a signed 12-hour JWT."""
        user = self.db.query(User).filter(User.username == payload.username.strip()).first()

        if not user or not verify_password(payload.password, user.password):
            self._log_auth_event(
                username=payload.username,
                status_msg="FAILED_BAD_CREDENTIALS",
                client_ip=client_ip,
                workstation=payload.workstation_name
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password."
            )

        # -------------------------------------------------------------------
        # Seamless Password Migration:
        # If the user's password in the DB is still plain text, hash it now!
        # -------------------------------------------------------------------
        if not user.password.startswith("$2"):
            user.password = hash_password(payload.password)
            self.db.commit()
            print(f"INFO: Legacy plain-text password for user '{user.username}' was upgraded to bcrypt.")

        # Track workstation terminal on user account
        if payload.workstation_name:
            user.workstation_name = payload.workstation_name.strip()
            self.db.commit()

        # Audit successful login
        self._log_auth_event(
            username=user.username,
            status_msg="SUCCESS",
            client_ip=client_ip,
            workstation=payload.workstation_name
        )

        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": str(user.role),
            "department": str(user.department)
        }
        token = create_access_token(data=token_data)

        return TokenResponse(
            access_token=token,
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=str(user.role),
            department=str(user.department)
        )

    def change_password(self, user: User, payload: ChangePasswordRequest) -> dict:
        """Allows an authenticated user to change their own password."""
        if not verify_password(payload.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed."
            )

        user.password = hash_password(payload.new_password)
        self.db.commit()
        return {"message": "Password updated successfully."}