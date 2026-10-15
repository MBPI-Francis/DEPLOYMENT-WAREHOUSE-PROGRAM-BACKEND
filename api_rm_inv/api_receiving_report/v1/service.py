"""
Business Service Layer for Receiving Reports.

Coordinates identifier resolution (codes to UUIDs), inventory SOH auto-provisioning,
and CRUD workflows for inbound raw materials.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status

from core.base import BaseService
from api_rm_inv.api_receiving_report.v1.crud import TempReceivingReportCRUD
from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_receiving_report.v1.schemas import (
    TempReceivingReportCreate,
    TempReceivingReportUpdate,
    TempReceivingReportResponse
)


class TempReceivingReportService(BaseService):
    """Business service coordinating inbound inventory receipt workflows."""

    def __init__(self, db):
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

    def create_receiving_report(self, payload: TempReceivingReportCreate) -> TempReceivingReportResponse:
        """
        Records an incoming shipment into the inventory ledger.
        Ensures a base StockOnHand row exists so balance calculation views remain stable.
        """
        rm_id, wh_id, st_id = self._resolve_foreign_keys(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name
        )

        # 1. Guarantee SOH initialization
        self.crud.ensure_stock_on_hand_initialized(rm_id, wh_id, st_id)

        # 2. Persist receiving report entry
        record = TempReceivingReport(
            rm_code_id=rm_id,
            warehouse_id=wh_id,
            status_id=st_id,
            ref_number=payload.ref_number.strip(),
            receiving_date=payload.receiving_date,
            qty_kg=payload.qty_kg,
            created_by_id=payload.created_by_id,
            is_deleted=False,
            is_cleared=False,
            is_adjusted=False
        )
        created = self.crud.create(record)

        # Return refreshed DTO
        active_list = self.crud.list_active()
        matched = next((item for item in active_list if item.id == created.id), None)
        if matched:
            return matched

        return created

    def get_receiving_report(self) -> List[dict]:
        """Retrieves active receiving reports for desktop grid display."""
        return self.crud.list_active()

    def get_deleted_receiving_report(self) -> List[dict]:
        """Retrieves soft-deleted reports for recovery/audit."""
        return self.crud.list_deleted()

    def get_historical_receiving_report(self, record_id: Optional[UUID] = None) -> List[dict]:
        """Retrieves computed historical receiving records."""
        return self.crud.list_historical(record_id)

    def update_receiving_report(self, report_id: UUID, payload: TempReceivingReportUpdate) -> List[dict]:
        """Updates an existing receiving report and returns the refreshed active list."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving Report record not found or has been deleted."
            )

        # Update Material if provided
        if payload.rm_code:
            material = self.crud.resolve_raw_material(payload.rm_code)
            if not material:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Material '{payload.rm_code}' not found.")
            record.rm_code_id = material.id

        # Update Warehouse if provided
        if payload.wh_number:
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{payload.wh_number}' not found.")
            record.warehouse_id = wh.id

        # Update Status if provided
        if payload.status_name:
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{payload.status_name}' not found.")
            record.status_id = st.id

        # Re-check SOH provisioning with updated keys
        self.crud.ensure_stock_on_hand_initialized(record.rm_code_id, record.warehouse_id, record.status_id)

        if payload.ref_number is not None:
            record.ref_number = payload.ref_number.strip()
        if payload.receiving_date is not None:
            record.receiving_date = payload.receiving_date
        if payload.qty_kg is not None:
            record.qty_kg = payload.qty_kg
        if payload.updated_by_id is not None:
            record.updated_by_id = payload.updated_by_id

        self.db.commit()
        return self.crud.list_active()

    def soft_delete_receiving_report(self, report_id: UUID) -> List[dict]:
        """Marks a receiving report as deleted and returns the refreshed active list."""
        record = self.crud.get_by_id(report_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receiving Report not found or already deleted."
            )

        record.is_deleted = True
        self.db.commit()
        return self.crud.list_active()

    def restore_receiving_report(self, report_id: UUID) -> List[dict]:
        """Restores a soft-deleted receiving report back to active status."""
        record = self.crud.get_by_id(report_id)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receiving Report is not in a deleted state."
            )

        record.is_deleted = False
        self.db.commit()
        return self.crud.list_active()