"""
Data Access Layer (CRUD) for Raw Materials.

Contains direct SQLAlchemy database queries and staged writes.
Kept strictly free of HTTP exceptions and explicit database commits.
"""

from typing import List, Optional, Tuple, Sequence
from uuid import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Session
from sqlalchemy.engine.row import RowMapping

from core.base import BaseRepository
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from api_rm_inv.api_raw_materials.v1.schemas import RawMaterialCreate, RawMaterialUpdate
from shared.users.models import User


class RawMaterialCRUD(BaseRepository):
    """Encapsulates all database interactions for the tbl_raw_materials table."""

    def get_by_id(self, rm_id: UUID, include_deleted: bool = False) -> Optional[RawMaterial]:
        """Fetches a raw material record by its internal primary UUID."""
        query = self.db.query(RawMaterial).filter(RawMaterial.id == rm_id)
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.first()

    def get_by_code(self, rm_code: str, include_deleted: bool = False) -> Optional[RawMaterial]:
        """
        Performs a case-insensitive lookup for a raw material by code,
        stripping spaces to prevent duplicate entries ('RM 101' vs 'RM101').
        """
        normalized_target = rm_code.replace(" ", "").upper()
        query = self.db.query(RawMaterial).filter(
            func.replace(func.upper(RawMaterial.rm_code), " ", "") == normalized_target
        )
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.first()

    def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[RawMaterial]:
        """Returns paginated raw materials sorted alphabetically by material code."""
        query = self.db.query(RawMaterial)
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.order_by(RawMaterial.rm_code.asc()).limit(limit).offset(offset).all()

    def get_all_transformed(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[dict]:
        """
        Queries active raw materials joined with the user table.
        Uses dictionary row mappings to eliminate ORM model instantiation overhead.
        """
        results = (
            self.db.query(
                RawMaterial.id,
                RawMaterial.rm_code,
                RawMaterial.rm_name,
                RawMaterial.type,
                RawMaterial.description,
                RawMaterial.created_at,
                RawMaterial.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User, User.id == RawMaterial.created_by_id)
            .filter(RawMaterial.is_deleted.is_(False))
            .order_by(RawMaterial.rm_code.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in results]

    def create(self, payload: RawMaterialCreate, user_id: Optional[UUID] = None) -> RawMaterial:
        """Stages a new raw material record without committing."""
        effective_user_id = user_id or payload.created_by_id

        item = RawMaterial(
            rm_code=payload.rm_code.strip().upper(),
            rm_name=payload.rm_name,
            description=payload.description,
            type=payload.type,
            created_by_id=effective_user_id
        )
        self.db.add(item)
        self.db.flush()  # Flushes SQL to allocate UUID primary key without closing the transaction
        return item

    def set_deleted_flag(self, item: RawMaterial, is_deleted: bool, user_id: Optional[UUID] = None) -> RawMaterial:
        """Toggles the soft-deleted status of a material record in the session."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.deleted_by_id = user_id
        self.db.flush()
        return item

    def bulk_create_ignore_duplicates(
        self,
        rm_codes: List[str],
        user_id: Optional[UUID] = None
    ) -> Tuple[int, int]:
        """
        High-performance bulk insert that checks existing codes in memory
        and saves all new records in the active transaction.
        """
        existing_codes = {
            row[0].strip().upper()
            for row in self.db.query(RawMaterial.rm_code).all()
        }

        new_records = []
        skipped_count = 0

        for code in rm_codes:
            cleaned_code = str(code).strip().upper()
            if not cleaned_code or cleaned_code in existing_codes:
                skipped_count += 1
                continue

            new_records.append(RawMaterial(rm_code=cleaned_code, created_by_id=user_id))
            existing_codes.add(cleaned_code)

        if new_records:
            self.db.bulk_save_objects(new_records)
            self.db.flush()

        return len(new_records), skipped_count

    def update(self, item: RawMaterial, payload: RawMaterialUpdate, user_id: UUID) -> RawMaterial:
        """Applies field updates to an existing RawMaterial record in the active transaction."""
        update_fields = payload.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field != "new_rm_code":
                setattr(item, field, value)

        item.updated_by_id = user_id
        self.db.flush()
        return item