"""
Business Service Layer for Receiving Reports.

Coordinates identifier resolution (codes to UUIDs), inventory SOH auto-provisioning,
atomic audit trail recording, and inbound raw material transactions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from api_rm_inv.api_receiving_report.v1.crud import TempReceivingReportCRUD
from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_receiving_report.v1.schemas import (
    TempReceivingReportCreate,
    TempReceivingReportUpdate,
    TempReceivingReportResponse
)
from core.logger import AuditLogger
from shared.users.models import User


class TempReceivingReportService(BaseService):
    """Business service coordinating inbound inventory receipt workflows."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = TempReceivingReportCRUD(db)

    def _resolve_foreign_keys(self, rm_code: str, wh_number: str, status_name: str) -> tuple[UUID, UUID, UUID]:
        """Resolves human business keys into internal UUID foreign keys."""
        material = self.crud.resolve_raw_material(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Raw Material with code '{rm_code}' does not exist in the catalog."
            )

        warehouse = self.crud.resolve_warehouse(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warehouse '{wh_number}' does not exist."
            )

        status_record = self.crud.resolve_status(status_name)
        if not status_record:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quality status '{status_name}' does not exist."
            )

        return material.id, warehouse.id, status_record.id

    def create_receiving_report(
        self,
        payload: TempReceivingReportCreate,
        request: Request,
        current_user: User
    ) -> TempReceivingReportResponse:
        """
        Records an incoming shipment into the inventory ledger.
        Ensures a base StockOnHand row exists and commits both data and audit log atomically.
        """
        rm_id, wh_id, st_id = self._resolve_foreign_keys(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name
        )

        try:
            # 1. Guarantee SOH initialization row exists
            self.crud.ensure_stock_on_hand_initialized(rm_id, wh_id, st_id)

            # 2. Persist receiving report entry
            record = TempReceivingReport(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                receiving_date=payload.receiving_date,
                qty_kg=payload.qty_kg,
                created_by_id=current_user.id,
                is_deleted=False,
                is_cleared=False,
                is_adjusted=False
            )
            created = self.crud.create(record)

            # 3. Stage Audit Log
            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_receiving_reports",
                record_id=created.id,
                payload=payload
            )

            # 4. Atomic Commit
            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_receiving_report(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves active receiving reports for desktop grid display."""
        return self.crud.list_active(limit=limit, offset=offset)

    def get_deleted_receiving_report(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves soft-deleted reports for recovery/audit."""
        return self.crud.list_deleted(limit=limit, offset=offset)

    def get_historical_receiving_report(
        self,
        record_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical receiving records."""
        return self.crud.list_historical(record_id=record_id, limit=limit, offset=offset)

    def update_receiving_report(
        self,
        report_id: UUID,
        payload: TempReceivingReportUpdate,
        request: Request,
        current_user: User
    ) -> TempReceivingReportResponse:
        """Updates an existing receiving report and records an audit log atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving Report record not found or has been deleted."
            )

        if payload.rm_code:
            material = self.crud.resolve_raw_material(payload.rm_code)
            if not material:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Material '{payload.rm_code}' not found.")
            record.rm_code_id = material.id

        if payload.wh_number:
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{payload.wh_number}' not found.")
            record.warehouse_id = wh.id

        if payload.status_name:
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{payload.status_name}' not found.")
            record.status_id = st.id

        try:
            self.crud.ensure_stock_on_hand_initialized(record.rm_code_id, record.warehouse_id, record.status_id)

            if payload.ref_number is not None:
                record.ref_number = payload.ref_number.strip()
            if payload.receiving_date is not None:
                record.receiving_date = payload.receiving_date
            if payload.qty_kg is not None:
                record.qty_kg = payload.qty_kg

            record.updated_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_receiving_reports",
                record_id=record.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_receiving_report(
        self,
        report_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Marks a receiving report as deleted and records the audit trail atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving Report not found or already deleted."
            )

        try:
            record.is_deleted = True
            record.deleted_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="SOFT_DELETE",
                table_name="tbl_receiving_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Receiving report soft-deleted successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_receiving_report(
        self,
        report_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted receiving report back to active status atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiving Report is not in a deleted state."
            )

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_receiving_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Receiving report restored successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e