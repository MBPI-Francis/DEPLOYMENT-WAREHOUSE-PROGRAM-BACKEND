"""
Business Service Layer for Form Entries Adjustments.

Coordinates parent-child transaction creation, foreign key resolution,
and cross-form linking for receiving, outgoing, prep, transfer, and status change corrections.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status

from core.base import BaseService
from api_rm_inv.api_adjustment_form.v1_form_entries.crud import AdjustmentFormCRUD
from api_rm_inv.api_adjustment_form.v1_form_entries.models import AdjustmentFormParent, AdjustmentFormCorrect
from api_rm_inv.api_adjustment_form.v1_form_entries.schemas import AdjustmentFormResponse

from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
from api_rm_inv.api_preparation_form.v1.models import TempPreparationForm
from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
from api_rm_inv.api_change_status_form.v1.models import TempHeldForm


class AdjustmentFormService(BaseService):
    """Business service coordinating form entry correction adjustments."""

    def __init__(self, db):
        super().__init__(db)
        self.crud = AdjustmentFormCRUD(db)

    def create_adjustment_form(self, payload: Any, form_type: str) -> Dict[str, Any]:
        """
        Creates an atomic parent-child correction adjustment using dedicated form payloads:
        - ReceivingAdjustmentCreate
        - OutgoingAdjustmentCreate
        - PreparationAdjustmentCreate
        - TransferAdjustmentCreate
        - ChangeStatusAdjustmentCreate
        """
        # 1. Resolve human business keys
        material = self.crud.resolve_raw_material(payload.rm_code)
        if not material:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Material '{payload.rm_code}' not found.")

        # 2. Create Parent Header
        parent = AdjustmentFormParent(
            ref_number=payload.ref_number.strip(),
            adjustment_date=payload.adjustment_date,
            referenced_date=payload.referenced_date,
            adjustment_type=payload.adjustment_type.strip(),
            responsible_person=payload.responsible_person.strip() if payload.responsible_person else None
        )
        self.db.add(parent)
        self.db.flush()

        # 3. Create Child Line with Form-Specific Fields
        child = AdjustmentFormCorrect(
            adjustment_parent_id=parent.id,
            rm_code_id=material.id,
            created_by_id=payload.created_by_id,
            is_deleted=False,
            is_cleared=False
        )

        if form_type == "receiving form":
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Warehouse '{payload.wh_number}' not found.")
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Status '{payload.status_name}' not found.")

            self.crud.ensure_stock_on_hand_initialized(material.id, wh.id, st.id)

            # Retire previous active correction if re-adjusting
            prev = self.db.query(AdjustmentFormCorrect).filter(
                AdjustmentFormCorrect.incorrect_receiving_id == payload.incorrect_receiving_id,
                AdjustmentFormCorrect.is_deleted.is_(False)
            ).first()
            if prev:
                prev.is_deleted = True

            child.warehouse_id = wh.id
            child.status_id = st.id
            child.qty_kg = payload.qty_kg
            child.incorrect_receiving_id = payload.incorrect_receiving_id

            orig = self.db.query(TempReceivingReport).filter(
                TempReceivingReport.id == payload.incorrect_receiving_id).first()
            if orig:
                orig.is_adjusted = True

        elif form_type == "outgoing form":
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Warehouse '{payload.wh_number}' not found.")
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Status '{payload.status_name}' not found.")

            self.crud.ensure_stock_on_hand_initialized(material.id, wh.id, st.id)

            prev = self.db.query(AdjustmentFormCorrect).filter(
                AdjustmentFormCorrect.incorrect_outgoing_id == payload.incorrect_outgoing_id,
                AdjustmentFormCorrect.is_deleted.is_(False)
            ).first()
            if prev:
                prev.is_deleted = True

            child.warehouse_id = wh.id
            child.status_id = st.id
            child.qty_kg = payload.qty_kg
            child.incorrect_outgoing_id = payload.incorrect_outgoing_id

            orig = self.db.query(TempOutgoingReport).filter(
                TempOutgoingReport.id == payload.incorrect_outgoing_id).first()
            if orig:
                orig.is_adjusted = True

        elif form_type == "preparation form":
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Warehouse '{payload.wh_number}' not found.")
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Status '{payload.status_name}' not found.")

            self.crud.ensure_stock_on_hand_initialized(material.id, wh.id, st.id)

            prev = self.db.query(AdjustmentFormCorrect).filter(
                AdjustmentFormCorrect.incorrect_preparation_id == payload.incorrect_preparation_id,
                AdjustmentFormCorrect.is_deleted.is_(False)
            ).first()
            if prev:
                prev.is_deleted = True

            child.warehouse_id = wh.id
            child.status_id = st.id
            child.qty_prepared = payload.qty_prepared
            child.qty_return = payload.qty_return
            child.incorrect_preparation_id = payload.incorrect_preparation_id

            orig = self.db.query(TempPreparationForm).filter(
                TempPreparationForm.id == payload.incorrect_preparation_id).first()
            if orig:
                orig.is_adjusted = True

        elif form_type == "transfer form":
            from_wh = self.crud.resolve_warehouse(payload.from_wh_number)
            to_wh = self.crud.resolve_warehouse(payload.to_wh_number)
            if not from_wh or not to_wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Invalid origin or destination warehouse.")
            if from_wh.id == to_wh.id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Origin and Destination warehouses cannot be identical.")

            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Status '{payload.status_name}' not found.")

            self.crud.ensure_stock_on_hand_initialized(material.id, to_wh.id, st.id)

            prev = self.db.query(AdjustmentFormCorrect).filter(
                AdjustmentFormCorrect.incorrect_transfer_id == payload.incorrect_transfer_id,
                AdjustmentFormCorrect.is_deleted.is_(False)
            ).first()
            if prev:
                prev.is_deleted = True

            child.from_warehouse_id = from_wh.id
            child.to_warehouse_id = to_wh.id
            child.status_id = st.id
            child.qty_kg = payload.qty_kg
            child.incorrect_transfer_id = payload.incorrect_transfer_id

            orig = self.db.query(TempTransferForm).filter(TempTransferForm.id == payload.incorrect_transfer_id).first()
            if orig:
                orig.is_adjusted = True

        elif form_type == "change status form":
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Warehouse '{payload.wh_number}' not found.")
            cur_st = self.crud.resolve_status(payload.current_status_name)
            new_st = self.crud.resolve_status(payload.new_status_name)
            if not cur_st or not new_st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Invalid current or new status.")
            if cur_st.id == new_st.id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Current and new status cannot be identical.")

            self.crud.ensure_stock_on_hand_initialized(material.id, wh.id, new_st.id)

            prev = self.db.query(AdjustmentFormCorrect).filter(
                AdjustmentFormCorrect.incorrect_change_status_id == payload.incorrect_change_status_id,
                AdjustmentFormCorrect.is_deleted.is_(False)
            ).first()
            if prev:
                prev.is_deleted = True

            child.warehouse_id = wh.id
            child.current_status_id = cur_st.id
            child.new_status_id = new_st.id
            child.qty_kg = payload.qty_kg
            child.incorrect_change_status_id = payload.incorrect_change_status_id

            orig = self.db.query(TempHeldForm).filter(TempHeldForm.id == payload.incorrect_change_status_id).first()
            if orig:
                orig.is_adjusted = True

        self.db.add(child)
        self.db.commit()
        self.db.refresh(parent)

        return {
            "message": f"Adjustment created successfully for {form_type}.",
            "parent_id": parent.id,
            "child_id": child.id,
            "ref_number": parent.ref_number
        }

    def get_adjustment_form(self) -> List[dict]:
        """Retrieves active adjustments for desktop grid display."""
        return self.crud.list_active()

    def get_deleted_adjustment_form(self) -> List[dict]:
        """Retrieves soft-deleted adjustments for recovery."""
        return self.crud.list_deleted()

    def get_historical_adjustment_form(
            self,
            record_id: Optional[UUID] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            rm_code: Optional[str] = None,
            limit: int = 50,
            offset: int = 0
    ) -> List[dict]:
        """Retrieves computed historical adjustments matching filter parameters with pagination."""
        return self.crud.list_historical(
            record_id=record_id,
            date_from=date_from,
            date_to=date_to,
            rm_code=rm_code,
            limit=limit,
            offset=offset
        )

    def update_adjustment_form(
            self,
            parent_id: UUID,
            payload: Any,
            form_type: str
    ) -> Dict[str, Any]:
        """
        Updates an existing adjustment using form-specific payloads:
        - ReceivingAdjustmentUpdate
        - OutgoingAdjustmentUpdate
        - PreparationAdjustmentUpdate
        - TransferAdjustmentUpdate
        - ChangeStatusAdjustmentUpdate
        """
        parent = self.crud.get_parent_by_id(parent_id)
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Adjustment record not found.")

        child = self.crud.get_child_by_parent_id(parent_id)
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Associated correction line not found or already deleted.")

        # 1. Update Common Header Fields
        if payload.ref_number is not None:
            parent.ref_number = payload.ref_number.strip()
        if payload.adjustment_date is not None:
            parent.adjustment_date = payload.adjustment_date
        if payload.referenced_date is not None:
            parent.referenced_date = payload.referenced_date
        if payload.adjustment_type is not None:
            parent.adjustment_type = payload.adjustment_type.strip()
        if payload.responsible_person is not None:
            parent.responsible_person = payload.responsible_person.strip()

        # 2. Update Material Code if provided
        if getattr(payload, "rm_code", None):
            mat = self.crud.resolve_raw_material(payload.rm_code)
            if not mat:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail=f"Material '{payload.rm_code}' not found.")
            child.rm_code_id = mat.id

        # 3. Update Form-Specific Fields
        if form_type in ["receiving form", "outgoing form", "preparation form"]:
            if getattr(payload, "wh_number", None):
                wh = self.crud.resolve_warehouse(payload.wh_number)
                if not wh:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Warehouse '{payload.wh_number}' not found.")
                child.warehouse_id = wh.id

            if getattr(payload, "status_name", None):
                st = self.crud.resolve_status(payload.status_name)
                if not st:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Status '{payload.status_name}' not found.")
                child.status_id = st.id

            if form_type == "preparation form":
                if payload.qty_prepared is not None:
                    child.qty_prepared = payload.qty_prepared
                if payload.qty_return is not None:
                    child.qty_return = payload.qty_return
            else:
                if payload.qty_kg is not None:
                    child.qty_kg = payload.qty_kg

        elif form_type == "transfer form":
            if payload.from_wh_number:
                from_wh = self.crud.resolve_warehouse(payload.from_wh_number)
                if not from_wh:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Origin warehouse '{payload.from_wh_number}' not found.")
                child.from_warehouse_id = from_wh.id

            if payload.to_wh_number:
                to_wh = self.crud.resolve_warehouse(payload.to_wh_number)
                if not to_wh:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Destination warehouse '{payload.to_wh_number}' not found.")
                child.to_warehouse_id = to_wh.id

            if child.from_warehouse_id == child.to_warehouse_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Origin and Destination warehouses cannot be identical.")

            if payload.status_name:
                st = self.crud.resolve_status(payload.status_name)
                if not st:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Status '{payload.status_name}' not found.")
                child.status_id = st.id

            if payload.qty_kg is not None:
                child.qty_kg = payload.qty_kg

        elif form_type == "change status form":
            if payload.wh_number:
                wh = self.crud.resolve_warehouse(payload.wh_number)
                if not wh:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Warehouse '{payload.wh_number}' not found.")
                child.warehouse_id = wh.id

            if payload.current_status_name:
                cur_st = self.crud.resolve_status(payload.current_status_name)
                if not cur_st:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"Current status '{payload.current_status_name}' not found.")
                child.current_status_id = cur_st.id

            if payload.new_status_name:
                new_st = self.crud.resolve_status(payload.new_status_name)
                if not new_st:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail=f"New status '{payload.new_status_name}' not found.")
                child.new_status_id = new_st.id

            if child.current_status_id == child.new_status_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="Current and new status cannot be identical.")

            if payload.qty_kg is not None:
                child.qty_kg = payload.qty_kg

        if getattr(payload, "updated_by_id", None):
            child.updated_by_id = payload.updated_by_id

        self.db.commit()
        return {
            "message": f"Adjustment for {form_type} updated successfully.",
            "parent_id": parent.id,
            "child_id": child.id
        }

    def soft_delete_adjustment_form(self, child_id: UUID) -> List[dict]:
        """Soft-deletes a correction entry and returns the refreshed active list."""
        child = self.crud.get_child_by_id(child_id)
        if not child or child.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Adjustment record not found or already deleted.")

        child.is_deleted = True
        self.db.commit()
        return self.crud.list_active()

    def restore_adjustment_form(self, child_id: UUID) -> AdjustmentFormResponse:
        """Restores a soft-deleted correction entry."""
        child = self.crud.get_child_by_id(child_id)
        if not child or not child.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Adjustment record is not in a deleted state.")

        child.is_deleted = False
        self.db.commit()

        active_list = self.crud.list_active()
        matched = next((item for item in active_list if item["id"] == child.id), None)
        if matched:
            return matched
        return child

    def validate_adjustment_form(
            self,
            form: str,
            incorrect_record_id: UUID,
            rm_id: UUID,
            warehouse_id: UUID,
            entered_qty: Decimal,
            status_id: UUID
    ) -> Dict[str, Any]:
        """
        Validates if an adjustment correction would cause negative stock in view_adjusted_ending_balance.
        """
        live_stock = self.crud.get_available_stock(rm_id, warehouse_id, status_id)

        # Check original record quantity
        original_qty = Decimal("0.00")
        if form == "outgoing":
            orig = self.db.query(TempOutgoingReport).filter(TempOutgoingReport.id == incorrect_record_id).first()
            if orig:
                original_qty = Decimal(str(orig.qty_kg))
        elif form == "receiving":
            orig = self.db.query(TempReceivingReport).filter(TempReceivingReport.id == incorrect_record_id).first()
            if orig:
                original_qty = Decimal(str(orig.qty_kg))

        # Effective balance if the original mistake is removed and the new value is applied
        effective_stock = live_stock + original_qty
        is_valid = entered_qty <= effective_stock

        return {
            "form": form,
            "live_stock": live_stock,
            "original_qty": original_qty,
            "entered_qty": entered_qty,
            "effective_available": effective_stock,
            "is_valid": is_valid,
            "message": "Valid adjustment" if is_valid else "Adjustment exceeds available stock."
        }