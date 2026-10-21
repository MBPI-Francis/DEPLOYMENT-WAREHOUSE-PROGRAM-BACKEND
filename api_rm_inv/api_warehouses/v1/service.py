"""
Business Service Layer for Warehouses.

Coordinates validation, duplicate number prevention,
atomic audit logging, and single-commit transactions.
"""

from typing import List, Dict, Any, Union
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

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

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = WarehouseCRUD(db)

    def create_warehouse(
        self,
        payload: WarehouseCreate,
        request: Request,
        current_user: User
    ) -> WarehouseResponse:
        """Ensures the warehouse number is unique and records the audit log atomically."""
        existing = self.crud.get_by_number(payload.wh_number, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Warehouse number '{payload.wh_number}' already exists."
            )

        try:
            created = self.crud.create(payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="INSERT",
                table_name="tbl_warehouses",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_warehouse(self, limit: int = 100, offset: int = 0) -> List[WarehouseResponse]:
        """Retrieves paginated active warehouses."""
        return self.crud.get_all(limit=limit, offset=offset)

    def all_transformed_warehouse_list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves active warehouses with creator audit metadata."""
        return self.crud.get_all_transformed(limit=limit, offset=offset)

    def update_warehouse_by_number(
        self,
        wh_number: Union[str, int],
        payload: WarehouseUpdate,
        request: Request,
        current_user: User
    ) -> WarehouseResponse:
        """Updates warehouse details and records an audit log atomically."""
        warehouse = self.crud.get_by_number(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse '{wh_number}' not found or already deleted."
            )

        if payload.new_wh_number and int(payload.new_wh_number) != warehouse.wh_number:
            new_num = int(payload.new_wh_number)
            collision = self.crud.get_by_number(new_num, include_deleted=True)
            if collision:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Warehouse number '{new_num}' is already taken."
                )
            warehouse.wh_number = new_num

        try:
            updated = self.crud.update(warehouse, payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="UPDATE",
                table_name="tbl_warehouses",
                record_id=updated.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(updated)
            return updated

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_warehouse_by_number(
        self,
        wh_number: Union[str, int],
        request: Request,
        current_user: User
    ) -> MessageResponse:
        """Soft-deletes a warehouse using its facility number atomically."""
        warehouse = self.crud.get_by_number(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Warehouse '{wh_number}' not found or already deleted."
            )

        try:
            self.crud.set_deleted_flag(warehouse, is_deleted=True, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="SOFT_DELETE",
                table_name="tbl_warehouses",
                record_id=warehouse.id,
                payload={"wh_number": wh_number, "action": "soft_delete"}
            )

            self.db.commit()
            return MessageResponse(
                message=f"Warehouse '{wh_number}' was successfully soft-deleted.",
                wh_number=str(wh_number)
            )

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_warehouse_by_number(
        self,
        wh_number: Union[str, int],
        request: Request,
        current_user: User
    ) -> MessageResponse:
        """Restores a soft-deleted warehouse atomically."""
        warehouse = self.crud.get_by_number(wh_number, include_deleted=True)
        if not warehouse or not warehouse.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse '{wh_number}' is not in a deleted state."
            )

        try:
            self.crud.set_deleted_flag(warehouse, is_deleted=False)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="RESTORE",
                table_name="tbl_warehouses",
                record_id=warehouse.id,
                payload={"wh_number": wh_number, "action": "restore"}
            )

            self.db.commit()
            return MessageResponse(
                message=f"Warehouse '{wh_number}' has been restored to active status.",
                wh_number=str(wh_number)
            )

        except Exception as e:
            self.db.rollback()
            raise e