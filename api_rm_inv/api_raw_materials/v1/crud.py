"""
Data Access Layer (CRUD) for Raw Materials.

Contains direct SQLAlchemy database queries and writes.
Kept strictly free of HTTP exceptions and request handling.
"""

from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.sql import func

from core.base import BaseRepository
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from api_rm_inv.api_raw_materials.v1.schemas import RawMaterialCreate, RawMaterialUpdate
from shared.users.models import User


class RawMaterialCRUD(BaseRepository):
    """Encapsulates all database interactions for the tbl_raw_materials table."""

    def get_by_id(self, rm_id: UUID, include_deleted: bool = False) -> Optional[RawMaterial]:
        """
        Fetches a raw material record by its internal primary UUID.

        Args:
            rm_id: The UUID of the raw material.
            include_deleted: If False, ignores soft-deleted records.
        """
        query = self.db.query(RawMaterial).filter(RawMaterial.id == rm_id)
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.first()

    def get_by_code(self, rm_code: str, include_deleted: bool = False) -> Optional[RawMaterial]:
        """
        Performs a case-insensitive lookup for a raw material by code,
        stripping out any spaces to prevent accidental duplicates like 'RM 101' vs 'RM101'.

        Args:
            rm_code: The material code string to look up.
            include_deleted: If True, searches both active and soft-deleted items.
        """
        normalized_target = rm_code.replace(" ", "").upper()
        query = self.db.query(RawMaterial).filter(
            func.replace(func.upper(RawMaterial.rm_code), " ", "") == normalized_target
        )
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.first()

    def get_all(self, include_deleted: bool = False) -> List[RawMaterial]:
        """Returns all raw materials sorted alphabetically by material code."""
        query = self.db.query(RawMaterial)
        if not include_deleted:
            query = query.filter(RawMaterial.is_deleted.is_(False))
        return query.order_by(RawMaterial.rm_code.asc()).all()

    def get_all_transformed(self) -> List[dict]:
        """
        Queries active raw materials and joins the shared User table to display
        the creator's readable full name.
        """
        return (
            self.db.query(
                RawMaterial.id,
                RawMaterial.rm_code,
                RawMaterial.rm_name,
                RawMaterial.created_at,
                RawMaterial.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User, User.id == RawMaterial.created_by_id)
            .filter(RawMaterial.is_deleted.is_(False))
            .order_by(RawMaterial.rm_code.asc())
            .all()
        )

    def create(self, payload: RawMaterialCreate) -> RawMaterial:
        """Persists a new raw material record to the database."""
        item = RawMaterial(
            rm_code=payload.rm_code.strip().upper(),
            rm_name=payload.rm_name,
            description=payload.description,
            type=payload.type,
            created_by_id=payload.created_by_id
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def set_deleted_flag(self, item: RawMaterial, is_deleted: bool, user_id: Optional[UUID] = None) -> RawMaterial:
        """Toggles the soft-deleted status of a material record."""
        item.is_deleted = is_deleted
        if is_deleted and user_id:
            item.deleted_by_id = user_id
        self.db.commit()
        self.db.refresh(item)
        return item

    def bulk_create_ignore_duplicates(self, rm_codes: List[str]) -> Tuple[int, int]:
        """
        High-performance bulk insert that checks existing codes in memory
        and saves all new records in a single database transaction.

        Returns:
            Tuple[int, int]: (count_inserted, count_skipped)
        """
        # Fetch all existing material codes from the DB in a single lightweight query
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

            new_records.append(RawMaterial(rm_code=cleaned_code))
            existing_codes.add(cleaned_code)  # Track so duplicates inside the same file are ignored

        if new_records:
            self.db.bulk_save_objects(new_records)
            self.db.commit()

        return len(new_records), skipped_count

    def update(self, item: RawMaterial, payload: RawMaterialUpdate) -> RawMaterial:
        """Applies field updates to an existing RawMaterial record."""
        update_fields = payload.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if field != "new_rm_code":  # handled in service if renaming code
                setattr(item, field, value)

        self.db.commit()
        self.db.refresh(item)
        return item