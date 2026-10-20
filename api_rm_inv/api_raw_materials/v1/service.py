"""
Business Service Layer for Raw Materials.

Coordinates data validation, business rules, natural key operations (rm_code),
and Excel bulk-import workflows.
"""

import io
from typing import List, Dict, Any
import pandas as pd
from fastapi import HTTPException, status, Request

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

    def __init__(self, db):
        super().__init__(db)
        self.crud = RawMaterialCRUD(db)

    def register_material(self, payload: RawMaterialCreate, request: Request,
                          current_user: User) -> RawMaterialResponse:
        existing = self.crud.get_by_code(payload.rm_code, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Raw material code '{payload.rm_code}' already exists."
            )

        # 1. Perform database write
        created_record = self.crud.create(payload)

        # 2. Record audit log entry
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

        return created_record

    def get_material_by_code(self, rm_code: str) -> RawMaterialResponse:
        """Fetches an active material by its code or raises HTTP 404 Not Found."""
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw material with code '{rm_code}' does not exist or has been deleted."
            )
        return material

    def get_all_materials(self) -> List[RawMaterialResponse]:
        """Retrieves all active raw materials for dropdowns and listing views."""
        return self.crud.get_all()

    def get_transformed_list(self) -> List[TransformedRawMaterialResponse]:
        """Retrieves active raw materials formatted with user audit metadata."""
        return self.crud.get_all_transformed()

    def update_material_by_code(
            self,
            rm_code: str,
            payload: RawMaterialUpdate,
            request: Request,
            current_user: User
    ) -> RawMaterialResponse:
        """
        Updates an existing raw material identified by its human-readable code.
        """
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Raw material '{rm_code}' not found."
            )

        # Handle material code rename if requested
        if payload.new_rm_code and payload.new_rm_code.strip().upper() != material.rm_code.upper():
            new_cleaned_code = payload.new_rm_code.strip().upper()
            collision = self.crud.get_by_code(new_cleaned_code, include_deleted=True)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot rename to '{new_cleaned_code}'; that material code already exists."
                )
            material.rm_code = new_cleaned_code

        # Update remaining attributes if provided
        if payload.rm_name is not None:
            material.rm_name = payload.rm_name
        if payload.description is not None:
            material.description = payload.description
        if payload.type is not None:
            material.type = payload.type

        # Track who updated it
        material.updated_by_id = current_user.id

        self.db.commit()
        self.db.refresh(material)

        # Record UPDATE event in the global audit log
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

        return material

    def soft_delete_material_by_code(self, rm_code: str, request: Request, current_user: User):
        material = self.crud.get_by_code(rm_code)
        if not material:
            raise HTTPException(status_code=404, detail=f"Material '{rm_code}' not found.")

        # 1. Perform database update
        self.crud.set_deleted_flag(material, is_deleted=True, user_id=current_user.id)

        # 2. Record audit log entry for soft delete
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

        return {"message": f"Raw material '{rm_code}' was successfully soft-deleted.", "rm_code": rm_code}

    def restore_material_by_code(self, rm_code: str, request: Request, current_user: User):
        material = self.crud.get_by_code(rm_code, include_deleted=True)
        if not material or not material.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Material '{rm_code}' is not deleted.")

        self.crud.set_deleted_flag(material, is_deleted=False)

        # Log RESTORE event
        AuditLogger.log_action(
            db=self.db, request=request, current_user=current_user,
            module="RM_INVENTORY", action="RESTORE",
            table_name="tbl_raw_materials", record_id=material.id, payload={"rm_code": rm_code}
        )
        return {"message": f"Raw material '{rm_code}' has been restored to active status.", "rm_code": rm_code}

    def process_excel_import(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Parses an uploaded Excel spreadsheet (.xlsx) and batch-inserts unique material codes.
        Guarantees that invalid sheets or bad columns fail with clear error messages.
        """
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

        inserted_count, skipped_count = self.crud.bulk_create_ignore_duplicates(raw_codes)

        return {
            "message": "Raw materials import completed successfully.",
            "successful_inserts": inserted_count,
            "skipped_duplicates": skipped_count,
        }