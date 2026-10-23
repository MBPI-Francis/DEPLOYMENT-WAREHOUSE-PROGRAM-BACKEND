"""
Business Service Layer for Spillage Adjustment Forms.

Coordinates business rules, foreign key resolution (rm_code, wh_number, status_name),
stock availability verification against schema_whrm.view_adjusted_ending_balance,
and atomic audit trail recording.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from api_rm_inv.api_adjustment_form.v1_spillage.crud import AdjustmentFormCRUD
from api_rm_inv.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
from api_rm_inv.api_adjustment_form.v1_spillage.schemas import (
    AdjustmentFormCreate,
    AdjustmentFormUpdate,
    AdjustmentFormResponse
)
from core.logger import AuditLogger
from shared.users.models import User


class AdjustmentFormService(BaseService):
    """Business service coordinating spillage loss records and stock availability checks."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = AdjustmentFormCRUD(db)

    def _resolve_and_validate_stock(
        self,
        rm_code: str,
        wh_number: str,
        status_name: str,
        requested_qty: Decimal,
        existing_spillage_qty: Decimal = Decimal("0.00")
    ) -> tuple[UUID, UUID, UUID]:
        """
        Resolves human business keys and validates algebraic stock balance:
        - Negative quantity = DEDUCTION. Validates stock will not drop below zero.
        - Positive quantity (+ or unsigned) = ADDITION. Allowed freely without overdraft checks.
        """
        if requested_qty == Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Adjustment quantity cannot be zero. Enter a negative value to deduct or positive value to add."
            )

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

        # Query live balance from schema_whrm.view_adjusted_ending_balance
        live_stock = self.crud.get_available_stock(material.id, warehouse.id, st.id)

        # On updates, base stock is live balance minus the previous entry's effect
        base_stock = live_stock - existing_spillage_qty
        projected_stock = base_stock + requested_qty

        # Overdraft check only triggers if the transaction would result in negative stock
        if projected_stock < Decimal("0.00"):
            available_to_deduct = max(Decimal("0.00"), base_stock)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for material '{rm_code}' in Warehouse '{wh_number}' "
                    f"under status '{status_name}'. "
                    f"Available stock: {available_to_deduct:.2f} kg, "
                    f"Requested deduction: {abs(requested_qty):.2f} kg "
                    f"(Deficit: {abs(projected_stock):.2f} kg)."
                )
            )

        return material.id, warehouse.id, st.id

    def create_adjustment_form(
        self,
        payload: AdjustmentFormCreate,
        request: Request,
        current_user: User
    ) -> AdjustmentFormResponse:
        """Validates warehouse stock availability and records a physical spillage loss atomically."""
        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name,
            requested_qty=payload.qty_kg,
            existing_spillage_qty=Decimal("0.00")
        )

        try:
            record = SpillageAdjustmentForm(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                spillage_form_number=payload.spillage_form_number.strip(),
                adjustment_date=payload.adjustment_date,
                reference_date=payload.reference_date,
                incident_date=payload.incident_date,
                qty_kg=payload.qty_kg,
                responsible_person=payload.responsible_person.strip(),
                reason=payload.reason.strip(),
                created_by_id=current_user.id,
                is_deleted=False,
                is_cleared=False
            )
            created = self.crud.create(record)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_spillage_forms",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_adjustment_form(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active spillage records for desktop grid display."""
        return self.crud.list_active(limit=limit, offset=offset)

    def get_deleted_adjustment_form(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted spillage records for recovery."""
        return self.crud.list_deleted(limit=limit, offset=offset)

    def get_historical_adjustment_form(
        self,
        record_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        rm_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        status_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical spillage records matching filter parameters."""
        return self.crud.list_historical(
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
            rm_code=rm_code,
            warehouse_name=warehouse_name,
            status_name=status_name,
            limit=limit,
            offset=offset
        )

    def update_adjustment_form(
        self,
        form_id: UUID,
        payload: AdjustmentFormUpdate,
        request: Request,
        current_user: User
    ) -> AdjustmentFormResponse:
        """Modifies an existing spillage record with live stock re-validation and audit logging."""
        record = self.crud.get_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spillage record not found or has been deleted."
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
            existing_spillage_qty=record.qty_kg
        )

        try:
            record.rm_code_id = rm_id
            record.warehouse_id = wh_id
            record.status_id = st_id
            record.qty_kg = target_qty
            record.updated_by_id = current_user.id

            if payload.ref_number is not None:
                record.ref_number = payload.ref_number.strip()
            if payload.spillage_form_number is not None:
                record.spillage_form_number = payload.spillage_form_number.strip()
            if payload.adjustment_date is not None:
                record.adjustment_date = payload.adjustment_date
            if payload.reference_date is not None:
                record.reference_date = payload.reference_date
            if payload.incident_date is not None:
                record.incident_date = payload.incident_date
            if payload.responsible_person is not None:
                record.responsible_person = payload.responsible_person.strip()
            if payload.reason is not None:
                record.reason = payload.reason.strip()

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_spillage_forms",
                record_id=record.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_adjustment_form(
        self,
        form_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Soft-deletes a spillage record and records an audit log atomically."""
        record = self.crud.get_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Spillage record not found or already deleted."
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
                table_name="tbl_spillage_forms",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Spillage record soft-deleted successfully.", "id": str(form_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_adjustment_form(
            self,
            form_id: UUID,
            request: Request,
            current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted spillage record after re-validating stock availability."""
        record = self.crud.get_by_id(form_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spillage record is not in a deleted state."
            )

        wh_num = str(record.warehouse_rel.wh_number) if record.warehouse_rel else "1"

        # Re-validate stock availability before allowing restore
        self._resolve_and_validate_stock(
            rm_code=record.raw_material,  # Dynamic property -> returns 'RM-1001'
            wh_number=wh_num,  # String -> '1'
            status_name=record.status or "good",  # Dynamic property -> returns 'good'
            requested_qty=record.qty_kg,
            existing_spillage_qty=Decimal("0.00")
        )

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_adjustment_spillage",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Spillage record restored successfully.", "id": str(form_id)}

        except Exception as e:
            self.db.rollback()
            raise e