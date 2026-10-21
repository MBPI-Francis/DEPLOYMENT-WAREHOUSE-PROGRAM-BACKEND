"""
Business Service Layer for Raw Materials.

Coordinates data validation, business rules, natural key operations (rm_code),
atomic audit trail recording, and Excel bulk-import workflows.
"""

import io
from typing import List, Dict, Any
import pandas as pd
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from api_rm_inv.api_raw_materials.v1.crud import RawMaterialCRUD
from api_rm_inv.api_raw_materials.v1.schemas import (
    RawMaterialCreate,
    RawMaterialUpdate,
    RawMaterialResponse,
    TransformedRawMaterialResponse,
    MessageResponse
)
from core.logger import AuditLogger
from shared.users.models import User


class RawMaterialService(BaseService):
    """Coordinates business rules and operations for Raw Materials."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = RawMaterialCRUD(db)

    def register_material(
        self,
        payload: RawMaterialCreate,
        request: Request,
        current_user: User
    ) -> RawMaterialResponse:
        """Registers a unique material and seals both record and audit log in one commit."""
        existing = self.crud.get_by_code(payload.rm_code, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Raw material code '{payload.rm_code}' already exists."
            )

        try:
            # 1. Stage database write
            created_record = self.crud.create(payload, user_id=current_user.id)

            # 2. Stage audit log in the same transaction
            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_raw_materials",
                record_id=created_record.id,
                payload=payload
            )

            # 3. Commit both atomically
            self.db.commit()
            self.db.refresh(created_record)
            return created_record
        except Exception as e:
            self.db.rollback()
            raise e

    def get_material_by_code(self, rm_code: str) -> RawMaterialResponse:
        """Fetches an active material by its code or raises HTTP 404."""
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw material with code '{rm_code}' does not exist or has been deleted."
            )
        return material

    def get_all_materials(self, limit: int = 100, offset: int = 0) -> List[RawMaterialResponse]:
        """Retrieves paginated active raw materials."""
        return self.crud.get_all(limit=limit, offset=offset)

    def get_transformed_list(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """Retrieves paginated raw materials formatted with user audit metadata."""
        return self.crud.get_all_transformed(limit=limit, offset=offset)

    def update_material_by_code(
        self,
        rm_code: str,
        payload: RawMaterialUpdate,
        request: Request,
        current_user: User
    ) -> RawMaterialResponse:
        """Updates an existing raw material and logs the modification atomically."""
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw material '{rm_code}' not found."
            )

        if payload.new_rm_code and payload.new_rm_code.strip().upper() != material.rm_code.upper():
            new_cleaned_code = payload.new_rm_code.strip().upper()
            collision = self.crud.get_by_code(new_cleaned_code, include_deleted=True)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot rename to '{new_cleaned_code}'; that material code already exists."
                )
            material.rm_code = new_cleaned_code

        try:
            updated_record = self.crud.update(material, payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_raw_materials",
                record_id=material.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(updated_record)
            return updated_record
        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_material_by_code(
        self,
        rm_code: str,
        request: Request,
        current_user: User
    ) -> MessageResponse:
        """Soft-deletes a material record and records the audit trail atomically."""
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material '{rm_code}' not found."
            )

        try:
            self.crud.set_deleted_flag(material, is_deleted=True, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="SOFT_DELETE",
                table_name="tbl_raw_materials",
                record_id=material.id,
                payload={"rm_code": rm_code, "action": "soft_delete"}
            )

            self.db.commit()
            return MessageResponse(
                message=f"Raw material '{rm_code}' was successfully soft-deleted.",
                rm_code=rm_code
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def restore_material_by_code(
        self,
        rm_code: str,
        request: Request,
        current_user: User
    ) -> MessageResponse:
        """Restores a soft-deleted raw material atomically."""
        material = self.crud.get_by_code(rm_code, include_deleted=True)
        if not material or not material.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Material '{rm_code}' is not deleted."
            )

        try:
            self.crud.set_deleted_flag(material, is_deleted=False)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_raw_materials",
                record_id=material.id,
                payload={"rm_code": rm_code}
            )

            self.db.commit()
            return MessageResponse(
                message=f"Raw material '{rm_code}' has been restored to active status.",
                rm_code=rm_code
            )
        except Exception as e:
            self.db.rollback()
            raise e

    def process_excel_import(
        self,
        file_bytes: bytes,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Parses an uploaded Excel spreadsheet and batch-inserts material codes."""
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not read the uploaded Excel file: {str(err)}"
            )

        if "rm_code" not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid file format. The spreadsheet must contain a column named 'rm_code'."
            )

        raw_codes = df["rm_code"].dropna().astype(str).tolist()
        if not raw_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded spreadsheet contains no valid raw material codes."
            )

        try:
            inserted_count, skipped_count = self.crud.bulk_create_ignore_duplicates(
                rm_codes=raw_codes,
                user_id=current_user.id
            )

            # Audit the bulk operation
            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_raw_materials",
                record_id=current_user.id,
                payload={"imported_count": inserted_count, "skipped_count": skipped_count}
            )

            self.db.commit()
            return {
                "message": "Raw materials import completed successfully.",
                "successful_inserts": inserted_count,
                "skipped_duplicates": skipped_count,
            }
        except Exception as e:
            self.db.rollback()
            raise e