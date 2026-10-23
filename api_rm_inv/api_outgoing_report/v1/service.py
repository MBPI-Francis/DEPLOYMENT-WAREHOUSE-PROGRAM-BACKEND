"""
Business Service Layer for Outgoing Reports (v1).

Coordinates data validation, business keys resolution (rm_code, wh_number, status_name),
stock availability verification against schema_whrm.view_adjusted_ending_balance,
and atomic audit trail recording.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from api_rm_inv.api_outgoing_report.v1.crud import TempOutgoingReportCRUD
from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
from api_rm_inv.api_outgoing_report.v1.schemas import (
    OutgoingFormCreate,
    OutgoingFormUpdate,
    OutgoingFormResponse
)
from core.logger import AuditLogger
from shared.users.models import User


class TempOutgoingReportService(BaseService):
    """Business service coordinating outbound material dispatch workflows."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = TempOutgoingReportCRUD(db)

    def _resolve_and_validate_stock(
        self,
        rm_code: str,
        wh_number: str,
        status_name: str,
        requested_qty: Decimal,
        existing_outgoing_qty: Decimal = Decimal("0.00")
    ) -> tuple[UUID, UUID, UUID]:
        """
        Resolves human business keys into UUIDs and validates available stock.
        Rejects the transaction if requested_qty > live_stock in the warehouse.
        """
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

        st = self.crud.resolve_status(status_name)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quality status '{status_name}' does not exist."
            )

        live_stock = self.crud.get_available_stock(material.id, warehouse.id, st.id)
        effective_stock = live_stock + existing_outgoing_qty

        if requested_qty > effective_stock:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for material '{rm_code}' in Warehouse '{wh_number}' "
                    f"under status '{status_name}'. "
                    f"Available stock: {effective_stock:.2f} kg, Requested dispatch: {requested_qty:.2f} kg."
                )
            )

        return material.id, warehouse.id, st.id

    def create_outgoing_report(
        self,
        payload: OutgoingFormCreate,
        request: Request,
        current_user: User
    ) -> OutgoingFormResponse:
        """Validates stock, stages outbound dispatch, and commits with audit log atomically."""
        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name,
            requested_qty=payload.qty_kg,
            existing_outgoing_qty=Decimal("0.00")
        )

        try:
            record = TempOutgoingReport(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                outgoing_date=payload.outgoing_date,
                qty_kg=payload.qty_kg,
                outgoing_type=payload.outgoing_type.strip().upper(),
                outgoing_destination=payload.outgoing_destination.strip() if payload.outgoing_destination else None,
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
                table_name="tbl_outgoing_reports",
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
        """Retrieves paginated active outgoing reports."""
        return self.crud.list_active(limit=limit, offset=offset)

    def get_deleted_outgoing_report(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted outgoing reports."""
        return self.crud.list_deleted(limit=limit, offset=offset)

    def get_historical_outgoing_report(
        self,
        record_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        rm_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        status_name: Optional[str] = None,
        outgoing_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical outgoing records matching filter parameters."""
        return self.crud.list_historical(
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
            rm_code=rm_code,
            warehouse_name=warehouse_name,
            status_name=status_name,
            outgoing_type=outgoing_type,
            limit=limit,
            offset=offset
        )

    def update_outgoing_report(
        self,
        report_id: UUID,
        payload: OutgoingFormUpdate,
        request: Request,
        current_user: User
    ) -> OutgoingFormResponse:
        """Modifies an existing outgoing report with live stock availability re-validation."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outgoing Report record not found or has been deleted."
            )

        target_rm = payload.rm_code or record.rm_code.rm_code
        target_wh = payload.wh_number or record.warehouse.wh_number
        target_status = payload.status_name or record.status.name
        target_qty = payload.qty_kg if payload.qty_kg is not None else record.qty_kg

        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=target_rm,
            wh_number=target_wh,
            status_name=target_status,
            requested_qty=target_qty,
            existing_outgoing_qty=record.qty_kg
        )

        try:
            record.rm_code_id = rm_id
            record.warehouse_id = wh_id
            record.status_id = st_id
            record.qty_kg = target_qty
            record.updated_by_id = current_user.id

            if payload.ref_number is not None:
                record.ref_number = payload.ref_number.strip()
            if payload.outgoing_date is not None:
                record.outgoing_date = payload.outgoing_date
            if payload.outgoing_type is not None:
                record.outgoing_type = payload.outgoing_type.strip().upper()
            if payload.outgoing_destination is not None:
                record.outgoing_destination = payload.outgoing_destination.strip()

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_outgoing_reports",
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
        """Soft-deletes an outgoing report and records an audit log atomically."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outgoing Report not found or already deleted."
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
                table_name="tbl_outgoing_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Outgoing report soft-deleted successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_outgoing_report(
            self,
            report_id: UUID,
            request: Request,
            current_user: User
    ) -> Dict[str, Any]:
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outgoing Report is not in a deleted state."
            )

        wh_num = str(record.warehouse_rel.wh_number) if record.warehouse_rel else "1"

        # Re-validate stock before allowing restore
        self._resolve_and_validate_stock(
            rm_code=record.raw_material,  # Uses property!
            wh_number=wh_num,
            status_name=record.status or "good",  # Uses property!
            requested_qty=record.qty_kg,
            existing_outgoing_qty=Decimal("0.00")
        )

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_outgoing_reports",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Outgoing report restored successfully.", "id": str(report_id)}

        except Exception as e:
            self.db.rollback()
            raise e