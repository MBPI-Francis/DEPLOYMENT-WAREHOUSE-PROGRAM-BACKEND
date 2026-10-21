"""
Business Service Layer for Warehouse Notes.

Coordinates validation, atomic audit logging, and single-commit transactions.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_notes.v1.crud import TempNotesCRUD
from api_rm_inv.api_notes.v1.models import TempNotes
from api_rm_inv.api_notes.v1.schemas import NotesCreate, NotesUpdate, NotesResponse


class NotesService(BaseService):
    """Business service coordinating warehouse notes and memos."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = TempNotesCRUD(db)

    def create_notes(
        self,
        payload: NotesCreate,
        request: Request,
        current_user: User
    ) -> TempNotes:
        """Validates foreign keys and persists note with audit log atomically."""
        kind = self.crud.resolve_product_kind(payload.product_kind_id)
        if not kind:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Product kind '{payload.product_kind_id}' does not exist."
            )

        try:
            created = self.crud.create_notes(payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_notes",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_notes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active notes."""
        return self.crud.get_notes(limit=limit, offset=offset)

    def get_deleted_notes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted notes."""
        return self.crud.get_deleted_notes(limit=limit, offset=offset)

    def get_historical_notes(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated historical notes."""
        return self.crud.get_historical_notes(limit=limit, offset=offset)

    def update_notes(
        self,
        notes_id: UUID,
        payload: NotesUpdate,
        request: Request,
        current_user: User
    ) -> TempNotes:
        """Modifies a note record and records an audit log atomically."""
        record = self.crud.get_by_id(notes_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note record not found or already deleted."
            )

        if payload.product_kind_id:
            kind = self.crud.resolve_product_kind(payload.product_kind_id)
            if not kind:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Product kind '{payload.product_kind_id}' does not exist."
                )

        try:
            updated = self.crud.update_notes(record, payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_notes",
                record_id=updated.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(updated)
            return updated

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_notes(
        self,
        notes_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Soft-deletes a note record and logs the action atomically."""
        record = self.crud.get_by_id(notes_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note record not found or already deleted."
            )

        try:
            self.crud.set_deleted_flag(record, is_deleted=True, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="SOFT_DELETE",
                table_name="tbl_notes",
                record_id=record.id,
                payload={"lot_number": record.lot_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Note record soft-deleted successfully.", "id": str(notes_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_notes(
        self,
        notes_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted note record atomically."""
        record = self.crud.get_by_id(notes_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Note record is not in a deleted state."
            )

        try:
            self.crud.set_deleted_flag(record, is_deleted=False)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_notes",
                record_id=record.id,
                payload={"lot_number": record.lot_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Note record restored successfully.", "id": str(notes_id)}

        except Exception as e:
            self.db.rollback()
            raise e