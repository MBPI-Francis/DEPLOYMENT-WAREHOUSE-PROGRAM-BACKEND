"""
Business Service Layer for Product Kinds.

Coordinates business rules, atomic transaction execution,
and system audit trail logging.
"""

from typing import List
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_product_kinds.v1.crud import ProductKindCRUD
from api_rm_inv.api_product_kinds.v1.schemas import ProductKindCreate, ProductKindUpdate, ProductKindResponse


class ProductKindService(BaseService):
    """Business service coordinating product kinds and audit logging."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = ProductKindCRUD(db)

    def create_product_kind(
        self,
        payload: ProductKindCreate,
        request: Request,
        current_user: User
    ) -> ProductKindResponse:
        """Validates unique classification code and stages record with audit log atomically."""
        existing = self.crud.get_by_id(payload.id, include_deleted=True)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product Kind with code '{payload.id}' already exists."
            )

        try:
            created = self.crud.create(payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="INSERT",
                table_name="tbl_product_kind",
                record_id=current_user.id,  # Use user_id for system audit if primary key is a string
                payload={"kind_id": created.id, "name": created.name, "description": created.description}
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def get_product_kind(self, limit: int = 100, offset: int = 0) -> List[ProductKindResponse]:
        """Retrieves paginated active product classification kinds."""
        return self.crud.get_all(limit=limit, offset=offset)

    def update_product_kind(
        self,
        product_kind_id: str,
        payload: ProductKindUpdate,
        request: Request,
        current_user: User
    ) -> ProductKindResponse:
        """Updates product kind details and commits with audit log atomically."""
        record = self.crud.get_by_id(product_kind_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product Kind not found or already deleted."
            )

        try:
            updated = self.crud.update(record, payload, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="UPDATE",
                table_name="tbl_product_kind",
                record_id=current_user.id,
                payload={"kind_id": product_kind_id, **payload.model_dump(exclude_unset=True)}
            )

            self.db.commit()
            self.db.refresh(updated)
            return updated

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_product_kind(
        self,
        product_kind_id: str,
        request: Request,
        current_user: User
    ) -> ProductKindResponse:
        """Soft-deletes a product classification kind atomically."""
        record = self.crud.get_by_id(product_kind_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product Kind not found or already deleted."
            )

        try:
            self.crud.set_deleted_flag(record, is_deleted=True, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="SOFT_DELETE",
                table_name="tbl_product_kind",
                record_id=current_user.id,
                payload={"kind_id": product_kind_id, "action": "soft_delete"}
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_product_kind(
        self,
        product_kind_id: str,
        request: Request,
        current_user: User
    ) -> ProductKindResponse:
        """Restores a soft-deleted product classification kind atomically."""
        record = self.crud.get_by_id(product_kind_id, include_deleted=True)
        if not record or not record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product Kind is not in a deleted state."
            )

        try:
            self.crud.set_deleted_flag(record, is_deleted=False, user_id=current_user.id)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="SYSTEM",
                action="RESTORE",
                table_name="tbl_product_kind",
                record_id=current_user.id,
                payload={"kind_id": product_kind_id, "action": "restore"}
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e