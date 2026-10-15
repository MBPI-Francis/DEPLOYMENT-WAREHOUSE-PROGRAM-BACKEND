"""
Business Service Layer for Quality Status Change (Held Form) Module.

Enforces inventory business rules:
- Prohibits changing to the identical status (current == new).
- Enforces strict stock balance validation against schema_whrm.view_adjusted_ending_balance,
  rejecting attempts to reclassify more stock than is physically available.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from core.base import BaseService
from api_rm_inv.api_change_status_form.v1.crud import TempHeldFormCRUD
from api_rm_inv.api_change_status_form.v1.models import TempHeldForm
from api_rm_inv.api_change_status_form.v1.schemas import (
    TempHeldFormCreate,
    TempHeldFormUpdate,
    TempHeldFormResponse
)


class TempHeldFormService(BaseService):
    """Business service coordinating QC status changes and stock availability checks."""

    def __init__(self, db):
        super().__init__(db)
        self.crud = TempHeldFormCRUD(db)

    def _resolve_and_validate(
        self,
        rm_code: str,
        wh_number: str,
        current_status_name: str,
        new_status_name: str,
        requested_qty: Decimal,
        existing_held_qty: Decimal = Decimal("0.00")
    ) -> tuple[UUID, UUID, UUID, UUID]:
        """
        Validates business rules and resolves codes into database UUIDs:
        1. Checks current != new status.
        2. Resolves material, warehouse, and status records.
        3. Validates requested_qty <= available_stock from view_adjusted_ending_balance.
        """
        # Rule 1: Cannot change to the identical status
        if current_status_name.strip().lower() == new_status_name.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Target status '{new_status_name}' cannot be identical to current status '{current_status_name}'."
            )

        material = self.crud.resolve_raw_material(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Raw Material with code '{rm_code}' does not exist in catalog."
            )

        warehouse = self.crud.resolve_warehouse(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warehouse '{wh_number}' does not exist."
            )

        current_st = self.crud.resolve_status(current_status_name)
        if not current_st:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Current quality status '{current_status_name}' does not exist."
            )

        new_st = self.crud.resolve_status(new_status_name)
        if not new_st:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"New target quality status '{new_status_name}' does not exist."
            )

        # Rule 2: Stock Availability Check against view_adjusted_ending_balance
        live_stock = self.crud.get_available_stock(material.id, warehouse.id, current_st.id)

        # On updates, add back the previously held quantity to avoid false-positive overdrafts
        effective_stock = live_stock + existing_held_qty

        if requested_qty > effective_stock:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Insufficient stock for raw material '{rm_code}' in Warehouse '{wh_number}' "
                    f"under status '{current_status_name}'. "
                    f"Available stock: {effective_stock:.2f} kg, Requested: {requested_qty:.2f} kg."
                )
            )

        return material.id, warehouse.id, current_st.id, new_st.id

    def create_held_form(self, payload: TempHeldFormCreate) -> TempHeldFormResponse:
        """
        Validates available stock and records a new quality status reclassification.
        """
        rm_id, wh_id, cur_st_id, new_st_id = self._resolve_and_validate(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            current_status_name=payload.current_status_name,
            new_status_name=payload.new_status_name,
            requested_qty=payload.qty_kg
        )

        record = TempHeldForm(
            rm_code_id=rm_id,
            warehouse_id=wh_id,
            current_status_id=cur_st_id,
            new_status_id=new_st_id,
            ref_number=payload.ref_number.strip(),
            change_status_date=payload.change_status_date,
            qty_kg=payload.qty_kg,
            created_by_id=payload.created_by_id,
            is_deleted=False,
            is_cleared=False,
            is_adjusted=False
        )
        created = self.crud.create(record)

        # Return full formatted DTO
        active_list = self.crud.list_active()
        matched = next((item for item in active_list if item["id"] == created.id), None)
        if matched:
            return matched

        return created

    def get_held_form(self) -> List[dict]:
        """Retrieves active status change records for desktop UI display."""
        return self.crud.list_active()

    def get_deleted_held_form(self) -> List[dict]:
        """Retrieves soft-deleted records for audit recovery."""
        return self.crud.list_deleted()

    def get_historical_held_form(
        self,
        record_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        rm_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        current_status_name: Optional[str] = None,
        new_status_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Retrieves computed historical status change records with pagination."""
        return self.crud.list_historical(
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
            rm_code=rm_code,
            warehouse_name=warehouse_name,
            current_status_name=current_status_name,
            new_status_name=new_status_name,
            limit=limit,
            offset=offset
        )

    def update_held_form(self, form_id: UUID, payload: TempHeldFormUpdate) -> List[dict]:
        """Modifies an existing status change record with stock validation."""
        record = self.crud.get_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Status Change record not found or has been deleted."
            )

        target_rm = payload.rm_code or record.rm_code.rm_code
        target_wh = payload.wh_number or record.warehouse.wh_number
        target_cur_st = payload.current_status_name or record.current_status.name
        target_new_st = payload.new_status_name or record.new_status.name
        target_qty = payload.qty_kg if payload.qty_kg is not None else record.qty_kg

        rm_id, wh_id, cur_st_id, new_st_id = self._resolve_and_validate(
            rm_code=target_rm,
            wh_number=target_wh,
            current_status_name=target_cur_st,
            new_status_name=target_new_st,
            requested_qty=target_qty,
            existing_held_qty=record.qty_kg  # Give credit for the quantity being modified
        )

        record.rm_code_id = rm_id
        record.warehouse_id = wh_id
        record.current_status_id = cur_st_id
        record.new_status_id = new_st_id
        record.qty_kg = target_qty

        if payload.ref_number is not None:
            record.ref_number = payload.ref_number.strip()
        if payload.change_status_date is not None:
            record.change_status_date = payload.change_status_date
        if payload.updated_by_id is not None:
            record.updated_by_id = payload.updated_by_id

        self.db.commit()
        return self.crud.list_active()

    def soft_delete_held_form(self, form_id: UUID) -> List[dict]:
        """Soft-deletes a status change entry and returns the refreshed active list."""
        record = self.crud.get_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Status Change record not found or already deleted."
            )

        record.is_deleted = True
        self.db.commit()
        return self.crud.list_active()

    def restore_held_form(self, form_id: UUID) -> List[dict]:
        """Restores a soft-deleted status change entry back to active status."""
        record = self.crud.get_by_id(form_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Status Change record is not in a deleted state."
            )

        # Before restoring, verify there is still sufficient stock in view_adjusted_ending_balance
        self._resolve_and_validate(
            rm_code=record.rm_code.rm_code,
            wh_number=record.warehouse.wh_number,
            current_status_name=record.current_status.name,
            new_status_name=record.new_status.name,
            requested_qty=record.qty_kg
        )

        record.is_deleted = False
        self.db.commit()
        return self.crud.list_active()