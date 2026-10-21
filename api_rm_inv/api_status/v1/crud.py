"""
Data Access Layer (CRUD) for Quality Status Module.

Contains direct SQLAlchemy database queries and writes.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.sql import func

from core.base import BaseRepository
from shared.statuses.models import Status
from shared.users.models import User
from api_rm_inv.api_status.v1.schemas import StatusCreate, StatusUpdate


class StatusCRUD(BaseRepository):
    """Encapsulates all database interactions for tbl_status."""

    def get_by_id(self, status_id: UUID, include_deleted: bool = False) -> Optional[Status]:
        """Fetches a quality status by its primary UUID."""
        query = self.db.query(Status).filter(Status.id == status_id)
        if not include_deleted:
            query = query.filter(Status.is_deleted.is_(False))
        return query.first()

    def get_by_name(self, name: str, include_deleted: bool = False) -> Optional[Status]:
        """Case-insensitive search for a status by name."""
        target = name.strip().lower()
        query = self.db.query(Status).filter(func.lower(Status.name) == target)
        if not include_deleted:
            query = query.filter(Status.is_deleted.is_(False))
        return query.first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Status]:
        """Returns paginated quality statuses ordered alphabetically."""
        query = self.db.query(Status)
        if not include_deleted:
            query = query.filter(Status.is_deleted.is_(False))
        return query.order_by(Status.name.asc()).limit(limit).offset(offset).all()

    def get_all_transformed(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves active statuses joined with creator full names as clean dictionaries."""
        records = (
            self.db.query(
                Status.id,
                Status.name,
                Status.description,
                Status.created_at,
                Status.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User, User.id == Status.created_by_id)
            .filter(Status.is_deleted.is_(False))
            .order_by(Status.name.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]

    def create(self, payload: StatusCreate, user_id: Optional[UUID] = None) -> Status:
        """Stages a new quality status in the active transaction."""
        effective_user_id = user_id or payload.created_by_id

        item = Status(
            name=payload.name.strip(),
            description=payload.description,
            created_by_id=effective_user_id
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: Status, payload: StatusUpdate, user_id: Optional[UUID] = None) -> Status:
        """Applies updates to an existing Status record in the active transaction."""
        update_fields = payload.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field != "new_name":
                setattr(item, field, value)

        if user_id:
            item.updated_by_id = user_id

        self.db.flush()
        return item

    def set_deleted_flag(self, item: Status, is_deleted: bool, user_id: Optional[UUID] = None) -> Status:
        """Toggles the soft-deleted state of a status record in the active transaction."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.deleted_by_id = user_id
        self.db.flush()
        return item