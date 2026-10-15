"""
Business Service Layer for Outgoing Reports (v2).

Coordinates data validation, business keys resolution (rm_code, wh_number, status_name),
and stock availability verification against schema_whrm.view_adjusted_ending_balance.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from core.base import BaseService
from api_rm_inv.api_outgoing_report.v1.crud import TempOutgoingReportCRUD
from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
from api_rm_inv.api_outgoing_report.v1.schemas import (
    OutgoingFormCreate,
    OutgoingFormUpdate,
    OutgoingFormResponse
)


class TempOutgoingReportService(BaseService):
    """Business service coordinating outbound material dispatch workflows."""

    def __init__(self, db):
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

        # Query live balance from view_adjusted_ending_balance
        live_stock = self.crud.get_available_stock(material.id, warehouse.id, st.id)

        # On updates, add back previously dispatched quantity to prevent false overdrafts
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

    def create_outgoing_report(self, payload: OutgoingFormCreate) -> OutgoingFormResponse:
        """
        Validates origin stock availability and records an outbound dispatch.
        """
        rm_id, wh_id, st_id = self._resolve_and_validate_stock(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name,
            requested_qty=payload.qty_kg,
            existing_outgoing_qty=Decimal("0.00")
        )

        record = TempOutgoingReport(
            rm_code_id=rm_id,
            warehouse_id=wh_id,
            status_id=st_id,
            ref_number=payload.ref_number.strip(),
            outgoing_date=payload.outgoing_date,
            qty_kg=payload.qty_kg,
            outgoing_type=payload.outgoing_type.strip().upper(),
            outgoing_destination=payload.outgoing_destination.strip() if payload.outgoing_destination else None,
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

    def get_outgoing_report(self) -> List[dict]:
        """Retrieves active outgoing reports for desktop grid display."""
        return self.crud.list_active()

    def get_deleted_outgoing_report(self) -> List[dict]:
        """Retrieves soft-deleted outgoing reports for recovery."""
        return self.crud.list_deleted()

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
    ) -> List[dict]:
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

    def update_outgoing_report(self, report_id: UUID, payload: OutgoingFormUpdate) -> List[dict]:
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

        record.rm_code_id = rm_id
        record.warehouse_id = wh_id
        record.status_id = st_id
        record.qty_kg = target_qty

        if payload.ref_number is not None:
            record.ref_number = payload.ref_number.strip()
        if payload.outgoing_date is not None:
            record.outgoing_date = payload.outgoing_date
        if payload.outgoing_type is not None:
            record.outgoing_type = payload.outgoing_type.strip().upper()
        if payload.outgoing_destination is not None:
            record.outgoing_destination = payload.outgoing_destination.strip()
        if payload.updated_by_id is not None:
            record.updated_by_id = payload.updated_by_id

        self.db.commit()
        return self.crud.list_active()

    def soft_delete_outgoing_report(self, report_id: UUID) -> List[dict]:
        """Soft-deletes an outgoing report and returns the refreshed active list."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Outgoing Report not found or already deleted."
            )

        record.is_deleted = True
        self.db.commit()
        return self.crud.list_active()

    def restore_outgoing_report(self, report_id: UUID) -> List[dict]:
        """Restores a soft-deleted outgoing report after re-validating stock availability."""
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Outgoing Report is not in a deleted state."
            )

        # Before restoring, verify warehouse still has enough stock to deduct
        self._resolve_and_validate_stock(
            rm_code=record.rm_code.rm_code,
            wh_number=record.warehouse.wh_number,
            status_name=record.status.name,
            requested_qty=record.qty_kg,
            existing_outgoing_qty=Decimal("0.00")
        )

        record.is_deleted = False
        self.db.commit()
        return self.crud.list_active()