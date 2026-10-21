"""
Data Access Layer (CRUD) for Warehouse Notes.

Contains direct queries and staged writes for tbl_notes in schema_whrm.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import or_, desc, func

from core.base import BaseRepository
from api_rm_inv.api_notes.v1.models import TempNotes
from api_rm_inv.api_notes.v1.schemas import NotesCreate, NotesUpdate
from api_rm_inv.api_product_kinds.v1.models import ProductKind
from shared.users.models import User


class TempNotesCRUD(BaseRepository):
    """Repository handling all database interactions for tbl_notes."""

    def resolve_product_kind(self, product_kind_id: str) -> Optional[ProductKind]:
        """Validates that the target product kind exists."""
        return (
            self.db.query(ProductKind)
            .filter(ProductKind.id == product_kind_id.strip().upper())
            .first()
        )

    def get_by_id(self, notes_id: UUID) -> Optional[TempNotes]:
        """Fetches a single note record by UUID."""
        return self.db.query(TempNotes).filter(TempNotes.id == notes_id).first()

    def create_notes(self, payload: NotesCreate, user_id: Optional[UUID] = None) -> TempNotes:
        """Stages a new note record in the active transaction."""
        effective_user_id = user_id or payload.created_by_id

        item = TempNotes(
            product_code=payload.product_code.strip(),
            lot_number=payload.lot_number.strip(),
            product_kind_id=payload.product_kind_id.strip().upper(),
            stock_change_date=payload.stock_change_date,
            created_by_id=effective_user_id,
            is_deleted=False,
            is_cleared=False
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_notes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active, un-cleared notes using dictionary mapping."""
        rows = (
            self.db.query(
                TempNotes.id,
                TempNotes.product_code,
                TempNotes.lot_number,
                TempNotes.product_kind_id,
                ProductKind.name.label("product_kind_name"),
                TempNotes.stock_change_date,
                TempNotes.created_at,
                TempNotes.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempNotes.date_computed
            )
            .join(ProductKind, TempNotes.product_kind_id == ProductKind.id)
            .outerjoin(User, TempNotes.created_by_id == User.id)
            .filter(
                or_(TempNotes.is_cleared.is_(None), TempNotes.is_cleared.is_(False)),
                or_(TempNotes.is_deleted.is_(None), TempNotes.is_deleted.is_(False))
            )
            .order_by(desc(TempNotes.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def get_deleted_notes(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted notes for audit recovery."""
        rows = (
            self.db.query(
                TempNotes.id,
                TempNotes.product_code,
                TempNotes.lot_number,
                TempNotes.product_kind_id,
                ProductKind.name.label("product_kind_name"),
                TempNotes.stock_change_date,
                TempNotes.created_at,
                TempNotes.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(ProductKind, TempNotes.product_kind_id == ProductKind.id)
            .outerjoin(User, TempNotes.created_by_id == User.id)
            .filter(TempNotes.is_deleted.is_(True))
            .order_by(desc(TempNotes.updated_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def get_historical_notes(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated historical computed notes."""
        rows = (
            self.db.query(
                TempNotes.id,
                TempNotes.product_code,
                TempNotes.lot_number,
                TempNotes.product_kind_id,
                ProductKind.name.label("product_kind_name"),
                TempNotes.stock_change_date,
                TempNotes.created_at,
                TempNotes.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempNotes.date_computed
            )
            .join(ProductKind, TempNotes.product_kind_id == ProductKind.id)
            .outerjoin(User, TempNotes.created_by_id == User.id)
            .filter(
                TempNotes.date_computed.is_not(None),
                or_(TempNotes.is_deleted.is_(None), TempNotes.is_deleted.is_(False))
            )
            .order_by(desc(TempNotes.date_computed))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def update_notes(self, item: TempNotes, payload: NotesUpdate, user_id: Optional[UUID] = None) -> TempNotes:
        """Applies field updates to an existing note in the active transaction."""
        update_fields = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
        for field, value in update_fields.items():
            setattr(item, field, value)

        if user_id:
            item.updated_by_id = user_id

        self.db.flush()
        return item

    def set_deleted_flag(self, item: TempNotes, is_deleted: bool, user_id: Optional[UUID] = None) -> TempNotes:
        """Toggles the soft-deleted state of a note in the session."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.deleted_by_id = user_id
        self.db.flush()
        return item