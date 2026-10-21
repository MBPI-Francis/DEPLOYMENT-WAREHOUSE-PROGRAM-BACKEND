"""
Data Access Layer (CRUD) for Warehouses.

Contains direct SQLAlchemy database queries and writes.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional, Union, Dict, Any
from uuid import UUID
from sqlalchemy.sql import func

from core.base import BaseRepository
from shared.warehouses.models import Warehouse
from shared.users.models import User
from api_rm_inv.api_warehouses.v1.schemas import WarehouseCreate, WarehouseUpdate


class WarehouseCRUD(BaseRepository):
    """Encapsulates all database interactions for the tbl_warehouses table."""

    def get_by_id(self, warehouse_id: UUID, include_deleted: bool = False) -> Optional[Warehouse]:
        """Fetches a warehouse by its primary UUID."""
        query = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id)
        if not include_deleted:
            query = query.filter(Warehouse.is_deleted.is_(False))
        return query.first()

    def get_by_number(self, wh_number: Union[str, int], include_deleted: bool = False) -> Optional[Warehouse]:
        """Fetches a warehouse by its unique facility number (smallint)."""
        try:
            target_int = int(str(wh_number).strip())
        except (ValueError, TypeError):
            return None

        query = self.db.query(Warehouse).filter(Warehouse.wh_number == target_int)
        if not include_deleted:
            query = query.filter(Warehouse.is_deleted.is_(False))
        return query.first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Warehouse]:
        """Returns paginated warehouses ordered by facility number."""
        query = self.db.query(Warehouse)
        if not include_deleted:
            query = query.filter(Warehouse.is_deleted.is_(False))
        return query.order_by(Warehouse.wh_number.asc()).limit(limit).offset(offset).all()

    def get_all_transformed(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves active warehouses joined with creator user details using dictionary mapping."""
        rows = (
            self.db.query(
                Warehouse.id,
                Warehouse.wh_number,
                Warehouse.wh_name,
                Warehouse.description,
                Warehouse.created_at,
                Warehouse.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User, User.id == Warehouse.created_by_id)
            .filter(Warehouse.is_deleted.is_(False))
            .order_by(Warehouse.wh_number.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def create(self, payload: WarehouseCreate, user_id: Optional[UUID] = None) -> Warehouse:
        """Stages a new warehouse record in the active transaction."""
        effective_user_id = user_id or payload.created_by_id

        item = Warehouse(
            wh_number=int(str(payload.wh_number).strip()),
            wh_name=payload.wh_name.strip(),
            description=payload.description,
            created_by_id=effective_user_id
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: Warehouse, payload: WarehouseUpdate, user_id: Optional[UUID] = None) -> Warehouse:
        """Applies updates to an existing Warehouse record in the session."""
        update_fields = payload.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field != "new_wh_number":
                setattr(item, field, value)

        if user_id:
            item.updated_by_id = user_id

        self.db.flush()
        return item

    def set_deleted_flag(self, item: Warehouse, is_deleted: bool, user_id: Optional[UUID] = None) -> Warehouse:
        """Toggles the soft-deleted state of a warehouse record in the session."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.deleted_by_id = user_id
        self.db.flush()
        return item