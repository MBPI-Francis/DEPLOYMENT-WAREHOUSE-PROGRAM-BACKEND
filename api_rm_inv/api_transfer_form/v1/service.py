"""
Business Service Layer for Transfer Forms.

Coordinates:
- Warehouse routing validation (preventing same-warehouse transfers).
- Stock overdraft validation against schema_whrm.view_adjusted_ending_balance
  to ensure the origin warehouse physically has sufficient stock.
- SOH baseline provisioning for the destination warehouse.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from core.base import BaseService
from api_rm_inv.api_transfer_form.v1.crud import TempTransferFormCRUD
from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
from api_rm_inv.api_transfer_form.v1.schemas import (
    TempTransferFormCreate,
    TempTransferFormUpdate,
    TempTransferFormResponse
)


class TempTransferFormService(BaseService):
    """Coordinates business rules and operations for internal stock transfers."""

    def __init__(self, db):
        super().__init__(db)
        self.crud = TempTransferFormCRUD(db)

    def _resolve_and_validate(
        self,
        rm_code: str,
        from_wh_number: str,
        to_wh_number: str,
        status_name: Optional[str],
        requested_qty: Decimal,
        existing_transfer_qty: Decimal = Decimal("0.00")
    ) -> tuple[UUID, UUID, UUID, Optional[UUID]]:
        """
        Validates business rules and resolves codes into database UUIDs:
        1. Ensures origin and destination warehouses are different.
        2. Resolves material, origin warehouse, destination warehouse, and status.
        3. Validates that the origin warehouse has sufficient live stock in
           schema_whrm.view_adjusted_ending_balance to fulfill the transfer.
        """
        # Rule 1: Cannot transfer to the exact same warehouse
        if from_wh_number.strip().lower() == to_wh_number.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Origin and Destination warehouses must be different. Cannot transfer stock to the same location."
            )

        material = self.crud.resolve_raw_material(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Raw Material with code '{rm_code}' does not exist in the catalog."
            )

        from_wh = self.crud.resolve_warehouse(from_wh_number)
        if not from_wh:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Origin warehouse '{from_wh_number}' does not exist."
            )

        to_wh = self.crud.resolve_warehouse(to_wh_number)
        if not to_wh:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Destination warehouse '{to_wh_number}' does not exist."
            )

        st_id = None
        effective_status_name = status_name or "good"
        st = self.crud.resolve_status(effective_status_name)
        if not st:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quality status '{effective_status_name}' does not exist."
            )
        st_id = st.id

        # Rule 2: Origin Warehouse Stock Availability Check
        live_stock = self.crud.get_available_stock(material.id, from_wh.id, st_id)

        # On updates, add back the previously transferred quantity to avoid false-positive overdrafts
        effective_stock = live_stock + existing_transfer_qty

        if requested_qty > effective_stock:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for raw material '{rm_code}' in Origin Warehouse '{from_wh_number}' "
                    f"under status '{effective_status_name}'. "
                    f"Available stock: {effective_stock:.2f} kg, Requested transfer: {requested_qty:.2f} kg."
                )
            )

        return material.id, from_wh.id, to_wh.id, st_id

    def create_transfer_form(self, payload: TempTransferFormCreate) -> TempTransferFormResponse:
        """
        Validates origin stock availability and records an internal transfer.
        Provisions a base SOH in the destination warehouse if this is the first time
        this material is stored there.
        """
        rm_id, from_wh_id, to_wh_id, st_id = self._resolve_and_validate(
            rm_code=payload.rm_code,
            from_wh_number=payload.from_wh_number,
            to_wh_number=payload.to_wh_number,
            status_name=payload.status_name,
            requested_qty=payload.qty_kg,
            existing_transfer_qty=Decimal("0.00")
        )

        # Ensure destination warehouse has an active SOH baseline
        self.crud.ensure_stock_on_hand_initialized(rm_id, to_wh_id, st_id)

        record = TempTransferForm(
            rm_code_id=rm_id,
            from_warehouse_id=from_wh_id,
            to_warehouse_id=to_wh_id,
            status_id=st_id,
            ref_number=payload.ref_number.strip(),
            transfer_date=payload.transfer_date,
            qty_kg=payload.qty_kg,
            created_by_id=payload.created_by_id,
            is_deleted=False,
            is_cleared=False,
            is_adjusted=False
        )
        created = self.crud.create(record)

        # Return full formatted DTO safely
        active_list = self.crud.list_active()
        matched = next(
            (
                item for item in active_list
                if (item["id"] if isinstance(item, dict) else getattr(item, "id", None)) == created.id
            ),
            None
        )
        if matched:
            return matched

        return created

    def get_transfer_form(self) -> List[dict]:
        """Retrieves active transfer records for desktop grid display."""
        return self.crud.list_active()

    def get_deleted_transfer_form(self) -> List[dict]:
        """Retrieves soft-deleted transfer records for recovery."""
        return self.crud.list_deleted()

    def get_historical_transfer_form(
        self,
        record_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        rm_code: Optional[str] = None,
        from_warehouse_name: Optional[str] = None,
        to_warehouse_name: Optional[str] = None,
        status_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Retrieves historical computed transfer records matching filter parameters with pagination."""
        return self.crud.list_historical(
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
            rm_code=rm_code,
            from_warehouse_name=from_warehouse_name,
            to_warehouse_name=to_warehouse_name,
            status_name=status_name,
            limit=limit,
            offset=offset
        )

    def update_transfer_form(self, transfer_id: UUID, payload: TempTransferFormUpdate) -> List[dict]:
        """Modifies an existing transfer form with origin stock re-validation."""
        record = self.crud.get_by_id(transfer_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer Form record not found or has been deleted."
            )

        target_rm = payload.rm_code or record.rm_code.rm_code
        target_from_wh = payload.from_wh_number or record.from_warehouse.wh_number
        target_to_wh = payload.to_wh_number or record.to_warehouse.wh_number
        target_status = payload.status_name or (record.status.name if record.status else "good")
        target_qty = payload.qty_kg if payload.qty_kg is not None else record.qty_kg

        # Validate stock availability in origin warehouse (giving credit for the existing record's weight)
        rm_id, from_wh_id, to_wh_id, st_id = self._resolve_and_validate(
            rm_code=target_rm,
            from_wh_number=target_from_wh,
            to_wh_number=target_to_wh,
            status_name=target_status,
            requested_qty=target_qty,
            existing_transfer_qty=record.qty_kg
        )

        record.rm_code_id = rm_id
        record.from_warehouse_id = from_wh_id
        record.to_warehouse_id = to_wh_id
        record.status_id = st_id
        record.qty_kg = target_qty

        # Re-check destination SOH provisioning with updated parameters
        self.crud.ensure_stock_on_hand_initialized(rm_id, to_wh_id, st_id)

        if payload.ref_number is not None:
            record.ref_number = payload.ref_number.strip()
        if payload.transfer_date is not None:
            record.transfer_date = payload.transfer_date
        if payload.updated_by_id is not None:
            record.updated_by_id = payload.updated_by_id

        self.db.commit()
        return self.crud.list_active()

    def soft_delete_transfer_form(self, transfer_id: UUID) -> List[dict]:
        """Soft-deletes a transfer record and returns the refreshed active list."""
        record = self.crud.get_by_id(transfer_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer Form not found or already deleted."
            )

        record.is_deleted = True
        self.db.commit()
        return self.crud.list_active()

    def restore_transfer_form(self, transfer_id: UUID) -> List[dict]:
        """Restores a soft-deleted transfer record after re-validating origin stock."""
        record = self.crud.get_by_id(transfer_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer Form is not in a deleted state."
            )

        # Before restoring, verify the origin warehouse still has enough stock to transfer
        self._resolve_and_validate(
            rm_code=record.rm_code.rm_code,
            from_wh_number=record.from_warehouse.wh_number,
            to_wh_number=record.to_warehouse.wh_number,
            status_name=record.status.name if record.status else "good",
            requested_qty=record.qty_kg,
            existing_transfer_qty=Decimal("0.00")
        )

        record.is_deleted = False
        self.db.commit()
        return self.crud.list_active()