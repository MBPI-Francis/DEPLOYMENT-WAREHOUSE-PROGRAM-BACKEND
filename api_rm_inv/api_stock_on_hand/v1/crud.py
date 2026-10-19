"""
Data Access Layer (CRUD) for Stock on Hand Module.

Contains direct queries, paginated historical balance listings,
and bulk database insertion utilities in schema_whrm.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func

from core.base import BaseRepository
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status


class StockOnHandCRUD(BaseRepository):
    """Repository handling all database queries and writes for tbl_stock_on_hand."""

    def resolve_raw_material(self, rm_code: str) -> Optional[RawMaterial]:
        """Looks up a material by code, ignoring spaces and case."""
        cleaned = rm_code.replace(" ", "").upper()
        return self.db.query(RawMaterial).filter(func.replace(func.upper(RawMaterial.rm_code), " ", "") == cleaned).first()

    def resolve_warehouse(self, wh_number: str) -> Optional[Warehouse]:
        """Looks up a warehouse by number or name."""
        target = str(wh_number).strip()
        wh = self.db.query(Warehouse).filter(Warehouse.wh_number == target).first()
        if wh:
            return wh
        return self.db.query(Warehouse).filter(Warehouse.wh_name.ilike(f"%{target}%")).first()

    def resolve_status(self, status_name: str) -> Optional[Status]:
        """Looks up a quality status by name."""
        return self.db.query(Status).filter(func.lower(Status.name) == status_name.strip().lower()).first()

    def get_latest_recalculation_count(self) -> int:
        """Finds the current maximum stock_recalculation_count in schema_whrm."""
        result = self.db.execute(text("SELECT MAX(stock_recalculation_count) FROM schema_whrm.tbl_stock_on_hand")).scalar()
        return (result + 1) if result is not None else 1

    def get_by_id(self, soh_id: UUID) -> Optional[StockOnHand]:
        """Fetches a single SOH record by UUID."""
        return self.db.query(StockOnHand).filter(StockOnHand.id == soh_id).first()

    def create(self, record: StockOnHand) -> StockOnHand:
        """Persists a new SOH record."""
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_all_paginated(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        Retrieves active SOH baseline records with pagination to prevent
        loading hundreds of thousands of rows into memory simultaneously.
        """
        records = (
            self.db.query(
                StockOnHand.id,
                RawMaterial.rm_code,
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                StockOnHand.rm_soh,
                StockOnHand.stock_recalculation_count,
                StockOnHand.stock_change_date,
                StockOnHand.date_computed,
                StockOnHand.description,
            )
            .join(RawMaterial, StockOnHand.rm_code_id == RawMaterial.id)
            .join(Warehouse, StockOnHand.warehouse_id == Warehouse.id)
            .outerjoin(Status, StockOnHand.status_id == Status.id)
            .filter(
                or_(StockOnHand.is_deleted.is_(None), StockOnHand.is_deleted.is_(False))
            )
            .order_by(desc(StockOnHand.stock_change_date))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]

    def get_historical_stock_on_hand(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Retrieves computed historical SOH records with multi-field filtering
        and pagination. Converts rows to dictionaries for high serialization throughput.
        """
        query = (
            self.db.query(
                StockOnHand.warehouse_id.label("wh_id"),
                Warehouse.wh_name.label("wh_name"),
                Warehouse.wh_number.label("wh_number"),
                StockOnHand.rm_code_id.label("rm_id"),
                RawMaterial.rm_code.label("rm_code"),
                StockOnHand.rm_soh.label("qty"),
                StockOnHand.stock_change_date.label("stock_change_date"),
                Status.name.label("status_name"),
                StockOnHand.status_id.label("status_id"),
                StockOnHand.date_computed
            )
            .join(RawMaterial, StockOnHand.rm_code_id == RawMaterial.id)
            .join(Warehouse, StockOnHand.warehouse_id == Warehouse.id)
            .outerjoin(Status, StockOnHand.status_id == Status.id)
            .filter(
                StockOnHand.date_computed.is_not(None),
                or_(StockOnHand.is_deleted.is_(None), StockOnHand.is_deleted.is_(False))
            )
        )

        if date_from and date_to:
            query = query.filter(and_(StockOnHand.date_computed >= date_from, StockOnHand.date_computed <= date_to))
        elif date_from:
            query = query.filter(StockOnHand.date_computed >= date_from)
        elif date_to:
            query = query.filter(StockOnHand.date_computed <= date_to)

        if mat_code and mat_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == mat_code.strip())

        if location and location.strip().lower() != "all":
            query = query.filter(Warehouse.wh_name == location.strip())

        if status and status.strip().lower() != "all":
            query = query.filter(func.lower(Status.name) == status.strip().lower())

        records = (
            query
            .order_by(desc(StockOnHand.date_computed), desc(StockOnHand.stock_change_date))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]

    def bulk_insert_soh(self, records: List[StockOnHand]) -> int:
        """Batch-inserts a list of SOH objects in a single atomic transaction."""
        if not records:
            return 0
        self.db.bulk_save_objects(records)
        self.db.commit()
        return len(records)