"""
Data Access Layer (CRUD) for Product Kinds.

Contains direct SQLAlchemy database queries and writes.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional
from uuid import UUID

from core.base import BaseRepository
from api_rm_inv.api_product_kinds.v1.models import ProductKind
from api_rm_inv.api_product_kinds.v1.schemas import ProductKindCreate, ProductKindUpdate


class ProductKindCRUD(BaseRepository):
    """Encapsulates database operations for tbl_product_kind."""

    def get_by_id(self, product_kind_id: str, include_deleted: bool = False) -> Optional[ProductKind]:
        """Fetches a product classification kind by its string identifier."""
        query = self.db.query(ProductKind).filter(ProductKind.id == product_kind_id.strip().upper())
        if not include_deleted:
            query = query.filter(ProductKind.is_deleted.is_(False))
        return query.first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[ProductKind]:
        """Returns paginated product classifications ordered alphabetically by name."""
        query = self.db.query(ProductKind)
        if not include_deleted:
            query = query.filter(ProductKind.is_deleted.is_(False))
        return query.order_by(ProductKind.name.asc()).limit(limit).offset(offset).all()

    def create(self, payload: ProductKindCreate, user_id: Optional[UUID] = None) -> ProductKind:
        """Stages a new product classification kind in the active transaction."""
        effective_user_id = user_id or payload.created_by_id

        item = ProductKind(
            id=payload.id.strip().upper(),
            name=payload.name.strip(),
            description=payload.description,
            created_by_id=effective_user_id,
            updated_by_id=payload.updated_by_id
        )
        self.db.add(item)
        self.db.flush()
        return item

    def update(self, item: ProductKind, payload: ProductKindUpdate, user_id: Optional[UUID] = None) -> ProductKind:
        """Applies field updates to an existing product classification kind in the session."""
        update_fields = payload.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(item, field, value)

        if user_id:
            item.updated_by_id = user_id

        self.db.flush()
        return item

    def set_deleted_flag(self, item: ProductKind, is_deleted: bool, user_id: Optional[UUID] = None) -> ProductKind:
        """Toggles the soft-deleted state of a product kind record in the session."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.updated_by_id = user_id
        self.db.flush()
        return item