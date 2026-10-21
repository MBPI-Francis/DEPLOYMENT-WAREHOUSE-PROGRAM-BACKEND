"""
Business Service Layer for Quality Status Module.

Coordinates status validation, renaming collision checks,
atomic audit logging, and single-commit database transactions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_status.v1.crud import StatusCRUD
from api_rm_inv.api_status.v1.schemas import (
    StatusCreate,
    StatusUpdate,
    StatusResponse,
    TransformedStatusResponse
)


class StatusService(BaseService):
    """Business service coordinating quality status lookups and audit logging."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = StatusCRUD(db)

    def create_status(
        self,
        payload: StatusCreate,
        request: Request,
        current_user: User
    ) -> StatusResponse:
        """Validates unique status name and records audit trail atomically."""
        existing = self.crud.get_by_name(payload.name, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Status '{payload.name}' already exists."
            )

        try:
            created = self.crud.create(payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="INSERT",
                table_name="tbl_status",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_status(self, limit: int = 100, offset: int = 0) -> List[StatusResponse]:
        """Retrieves paginated active quality statuses."""
        return self.crud.get_all(limit=limit, offset=offset)

    def all_transformed_status(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active statuses with creator audit metadata."""
        return self.crud.get_all_transformed(limit=limit, offset=offset)

    def get_status_by_name(self, name: str) -> Dict[str, Any]:
        """Looks up a specific status by name."""
        status_rec = self.crud.get_by_name(name)
        if not status_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status '{name}' not found."
            )
        return {"id": status_rec.id, "name": status_rec.name}

    def update_status_by_name(
        self,
        name: str,
        payload: StatusUpdate,
        request: Request,
        current_user: User
    ) -> StatusResponse:
        """Updates quality status details and records audit trail atomically."""
        status_rec = self.crud.get_by_name(name)
        if not status_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status '{name}' not found."
            )

        if payload.new_name and payload.new_name.strip().lower() != status_rec.name.lower():
            new_clean = payload.new_name.strip()
            collision = self.crud.get_by_name(new_clean, include_deleted=True)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Status name '{new_clean}' already taken."
                )
            status_rec.name = new_clean

        try:
            updated = self.crud.update(status_rec, payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="UPDATE",
                table_name="tbl_status",
                record_id=updated.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(updated)
            return updated

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_status_by_name(
        self,
        name: str,
        request: Request,
        current_user: User
    ) -> StatusResponse:
        """Soft-deletes a status record and logs the action atomically."""
        status_rec = self.crud.get_by_name(name)
        if not status_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Status '{name}' not found."
            )

        try:
            self.crud.set_deleted_flag(status_rec, is_deleted=True, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="SOFT_DELETE",
                table_name="tbl_status",
                record_id=status_rec.id,
                payload={"name": name, "action": "soft_delete"}
            )

            self.db.commit()
            self.db.refresh(status_rec)
            return status_rec

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_status_by_name(
        self,
        name: str,
        request: Request,
        current_user: User
    ) -> StatusResponse:
        """Restores a soft-deleted quality status atomically."""
        status_rec = self.crud.get_by_name(name, include_deleted=True)
        if not status_rec or not status_rec.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status '{name}' is not in a deleted state."
            )

        try:
            self.crud.set_deleted_flag(status_rec, is_deleted=False)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="RESTORE",
                table_name="tbl_status",
                record_id=status_rec.id,
                payload={"name": name, "action": "restore"}
            )

            self.db.commit()
            self.db.refresh(status_rec)
            return status_rec

        except Exception as e:
            self.db.rollback()
            raise e