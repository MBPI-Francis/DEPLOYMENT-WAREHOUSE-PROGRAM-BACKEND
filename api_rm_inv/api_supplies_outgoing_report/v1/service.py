"""
Business Service Layer for Supplies Outgoing Reports.

Coordinates supplies validation, identifier resolution (codes to UUIDs),
atomic audit logging, and single-commit transaction execution.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_supplies_outgoing_report.v1.crud import SuppliesOutgoingReportCRUD
from api_rm_inv.api_supplies_outgoing_report.v1.models import SuppliesOutgoingReport
from api_rm_inv.api_supplies_outgoing_report.v1.schemas import (
    SuppliesOutgoingFormCreate,
    SuppliesOutgoingFormUpdate,
    SuppliesOutgoingFormResponse
)


class SuppliesOutgoingFormService(BaseService):
    """Business service coordinating supplies outbound dispatches."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = SuppliesOutgoingReportCRUD(db)

    def _resolve_foreign_keys(self, payload: SuppliesOutgoingFormCreate) -> tuple[UUID, UUID, UUID]:
        """Resolves natural keys or UUIDs into guaranteed database UUIDs."""
        # 1. Resolve Supply Material
        rm_id = payload.rm_code_id
        if not rm_id and hasattr(payload, "rm_code") and payload.rm_code:
            mat = self.crud.resolve_supply_material(payload.rm_code)
            if not mat:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Supply material '{payload.rm_code}' not found.")
            rm_id = mat.id

        # 2. Resolve Warehouse
        wh_id = payload.warehouse_id
        if not wh_id and hasattr(payload, "wh_number") and payload.wh_number:
            wh = self.crud.resolve_warehouse(str(payload.wh_number))
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{payload.wh_number}' not found.")
            wh_id = wh.id

        # 3. Resolve Status
        st_id = payload.status_id
        if not st_id and hasattr(payload, "status_name") and payload.status_name:
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{payload.status_name}' not found.")
            st_id = st.id

        if not all([rm_id, wh_id, st_id]):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing required material, warehouse, or status identifiers.")

        return rm_id, wh_id, st_id

    def create_outgoing_report(
        self,
        payload: SuppliesOutgoingFormCreate,
        request: Request,
        current_user: User
    ) -> SuppliesOutgoingReport:
        """Records an outbound supplies dispatch and logs the event atomically."""
        rm_id, wh_id, st_id = self._resolve_foreign_keys(payload)

        try:
            record = SuppliesOutgoingReport(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                outgoing_date=payload.outgoing_date,
                qty_kg=payload.qty_kg,
                created_by_id=current_user.id,
                is_deleted=False,
                is_cleared=False,
                is_adjusted=False
            )
            created = self.crud.create(record)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_supplies_outgoing_reports",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_outgoing_report(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active supplies outgoing reports."""
        return self.crud.list_active(limit=limit, offset=offset)

    def get_deleted_outgoing_report(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted supplies reports."""
        return self.crud.list_deleted(limit=limit, offset=offset)

    def get_historical_outgoing_report(
        self,
        record_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves paginated historical computed supplies reports."""
        return self.crud.list_historical(record_id=record_id, limit=limit, offset=offset)

    def update_outgoing_report(
        self,
        report_id: UUID,
        payload: SuppliesOutgoingFormUpdate,
        request: Request,
        current_user: User
    ) -> SuppliesOutgoingReport:
        """Modifies a supplies outgoing report and records an audit log atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplies outgoing report not found or already deleted.")

        try:
            update_data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(record, key, value)

            record.updated_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_supplies_outgoing_reports",
                record_id=record.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_outgoing_report(
        self,
        report_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Soft-deletes a supplies report and logs the action atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplies outgoing report not found or already deleted.")

        try:
            record.is_deleted = True
            record.deleted_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="SOFT_DELETE",
                table_name="tbl_supplies_outgoing_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Supplies outgoing report soft-deleted successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_outgoing_report(
        self,
        report_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted supplies report atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplies outgoing report is not in a deleted state.")

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_supplies_outgoing_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Supplies outgoing report restored successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e