"""
Business Service Layer for Supplies Outgoing Reports.

Coordinates natural business key resolution (rm_code, wh_number, status_name),
live stock overdraft checks, atomic audit logging, and single-commit transactions.
"""

from decimal import Decimal
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
    SuppliesOutgoingFormUpdate
)


class SuppliesOutgoingFormService(BaseService):
    """Business service coordinating supplies outbound dispatches."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = SuppliesOutgoingReportCRUD(db)

    def _resolve_and_validate_stock(
        self,
        rm_code: str,
        wh_number: str,
        status_name: str,
        requested_qty: Decimal,
        existing_qty: Decimal = Decimal("0.00")
    ) -> tuple[UUID, UUID, UUID]:
        """
        Resolves human business keys into database UUIDs and checks live stock:
        1. Material lookup by rm_code.
        2. Warehouse lookup by wh_number.
        3. Status lookup by status_name.
        4. Validates requested_qty <= live stock in view_adjusted_ending_balance.
        """
        # 1. Resolve Material
        mat = self.crud.resolve_supply_material(rm_code)
        if not mat:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Supply material with code '{rm_code}' does not exist in catalog."
            )

        # 2. Resolve Warehouse
        wh = self.crud.resolve_warehouse(wh_number)
        if not wh:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warehouse '{wh_number}' does not exist."
            )

        # 3. Resolve Status
        effective_status = status_name.strip() if status_name else "good"
        st = self.crud.resolve_status(effective_status)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quality status '{effective_status}' does not exist."
            )

        # 4. Live Stock Balance Check
        live_stock = self.crud.get_available_stock(mat.id, wh.id, st.id)
        effective_stock = live_stock + existing_qty

        if requested_qty > effective_stock:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for supply item '{rm_code}' in Warehouse '{wh_number}' "
                    f"under status '{effective_status}'. "
                    f"Available stock: {effective_stock:.2f} kg, Requested dispatch: {requested_qty:.2f} kg."
                )
            )

        return mat.id, wh.id, st.id

    def create_outgoing_report(
        self,
        payload: SuppliesOutgoingFormCreate,
        request: Request,
        current_user: User
    ) -> SuppliesOutgoingReport:
        """Records an outbound supplies dispatch using pure human business keys."""
        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name,
            requested_qty=payload.qty_kg,
            existing_qty=Decimal("0.00")
        )

        try:
            record = SuppliesOutgoingReport(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                outgoing_date=payload.outgoing_date,
                qty_kg=payload.qty_kg,
                created_by_id=current_user.id,  # Stamped from JWT / X-API-Key
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
        """Modifies a supplies outgoing report with live stock re-validation."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplies outgoing report not found or already deleted."
            )

        target_rm = payload.rm_code or record.raw_material
        target_wh = payload.wh_number or (str(record.warehouse_rel.wh_number) if record.warehouse_rel else "1")
        target_status = payload.status_name or record.status
        target_qty = payload.qty_kg if payload.qty_kg is not None else record.qty_kg

        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=target_rm,
            wh_number=target_wh,
            status_name=target_status,
            requested_qty=target_qty,
            existing_qty=record.qty_kg
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
        """Restores a soft-deleted supplies report after re-validating stock availability."""
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplies outgoing report is not in a deleted state.")

        wh_num = str(record.warehouse_rel.wh_number) if record.warehouse_rel else "1"

        self._resolve_and_validate_stock(
            rm_code=record.raw_material,
            wh_number=wh_num,
            status_name=record.status or "good",
            requested_qty=record.qty_kg,
            existing_qty=Decimal("0.00")
        )

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