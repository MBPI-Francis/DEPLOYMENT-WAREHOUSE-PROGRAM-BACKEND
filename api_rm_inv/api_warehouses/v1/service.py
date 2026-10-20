"""
Business Service Layer for Warehouses.

Coordinates validation, duplicate number prevention, and audit log recording.
"""

from typing import List
from fastapi import HTTPException, status, Request

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_warehouses.v1.crud import WarehouseCRUD
from api_rm_inv.api_warehouses.v1.schemas import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    TransformedWarehouseResponse,
    MessageResponse
)


class WarehouseService(BaseService):
    """Coordinates business rules and operations for physical warehouses."""

    def __init__(self, db):
        super().__init__(db)
        self.crud = WarehouseCRUD(db)

    def create_warehouse(self, payload: WarehouseCreate, request: Request, current_user: User) -> WarehouseResponse:
        """Ensures the warehouse number is unique before saving."""
        existing = self.crud.get_by_number(payload.wh_number, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warehouse number '{payload.wh_number}' already exists."
            )

        payload.created_by_id = current_user.id
        created = self.crud.create(payload)

        # Record audit log
        AuditLogger.log_action(
            db=self.db, request=request, current_user=current_user,
            module="RM_INVENTORY", action="INSERT",
            table_name="tbl_warehouses", record_id=created.id, payload=payload
        )
        return created

    def get_warehouse(self) -> List[WarehouseResponse]:
        """Retrieves all active warehouses."""
        return self.crud.get_all()

    def all_transformed_warehouse_list(self) -> List[TransformedWarehouseResponse]:
        """Retrieves active warehouses with creator audit metadata."""
        return self.crud.get_all_transformed()

    def update_warehouse_by_number(
            self,
            wh_number: str,
            payload: WarehouseUpdate,
            request: Request,
            current_user: User
    ) -> WarehouseResponse:
        """Updates warehouse details identified by its facility number."""
        warehouse = self.crud.get_by_number(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse '{wh_number}' not found or already deleted."
            )

        if payload.new_wh_number and str(payload.new_wh_number).strip() != str(warehouse.wh_number):
            new_num = str(payload.new_wh_number).strip()
            collision = self.crud.get_by_number(new_num, include_deleted=True)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Warehouse number '{new_num}' is already taken."
                )
            warehouse.wh_number = new_num

        updated = self.crud.update(warehouse, payload)

        # Record audit log
        AuditLogger.log_action(
            db=self.db, request=request, current_user=current_user,
            module="RM_INVENTORY", action="UPDATE",
            table_name="tbl_warehouses", record_id=updated.id, payload=payload
        )
        return updated

    def soft_delete_warehouse_by_number(self, wh_number: str, request: Request, current_user: User) -> MessageResponse:
        """Soft-deletes a warehouse using its facility number."""
        warehouse = self.crud.get_by_number(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse '{wh_number}' not found or already deleted."
            )

        self.crud.set_deleted_flag(warehouse, is_deleted=True)

        # Record audit log
        AuditLogger.log_action(
            db=self.db, request=request, current_user=current_user,
            module="RM_INVENTORY", action="SOFT_DELETE",
            table_name="tbl_warehouses", record_id=warehouse.id, payload={"wh_number": wh_number}
        )
        return MessageResponse(message=f"Warehouse '{wh_number}' was successfully soft-deleted.", wh_number=wh_number)

    def restore_warehouse_by_number(self, wh_number: str, request: Request, current_user: User) -> MessageResponse:
        """Restores a soft-deleted warehouse."""
        warehouse = self.crud.get_by_number(wh_number, include_deleted=True)
        if not warehouse or not warehouse.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse '{wh_number}' is not in a deleted state."
            )

        self.crud.set_deleted_flag(warehouse, is_deleted=False)

        # Record audit log
        AuditLogger.log_action(
            db=self.db, request=request, current_user=current_user,
            module="RM_INVENTORY", action="RESTORE",
            table_name="tbl_warehouses", record_id=warehouse.id, payload={"wh_number": wh_number}
        )
        return MessageResponse(message=f"Warehouse '{wh_number}' has been restored to active status.",
                               wh_number=wh_number)