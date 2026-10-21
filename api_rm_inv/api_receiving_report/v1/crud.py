"""
Data Access Layer (CRUD) for Receiving Reports.

Handles database queries, staged writes, and StockOnHand auto-initialization in schema_whrm.
Strictly free of manual commits and HTTP exceptions.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import text, desc, or_, func

from core.base import BaseRepository
from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class TempReceivingReportCRUD(BaseRepository):
    """Repository handling database operations for inbound receiving reports."""

    def resolve_raw_material(self, rm_code: str) -> Optional[RawMaterial]:
        """Looks up a material by its business code, ignoring spaces and case."""
        cleaned = rm_code.replace(" ", "").upper()
        return (
            self.db.query(RawMaterial)
            .filter(func.replace(func.upper(RawMaterial.rm_code), " ", "") == cleaned)
            .first()
        )

    def resolve_warehouse(self, wh_number: str) -> Optional[Warehouse]:
        """Looks up a warehouse by number or friendly name."""
        target = str(wh_number).strip()
        wh = self.db.query(Warehouse).filter(Warehouse.wh_number == target).first()
        if wh:
            return wh
        return self.db.query(Warehouse).filter(Warehouse.wh_name.ilike(f"%{target}%")).first()

    def resolve_status(self, status_name: str) -> Optional[Status]:
        """Looks up a quality status by normalized name."""
        return (
            self.db.query(Status)
            .filter(func.lower(Status.name) == status_name.strip().lower())
            .first()
        )

    def ensure_stock_on_hand_initialized(self, rm_id: UUID, wh_id: UUID, status_id: UUID) -> None:
        """
        Guarantees that a base StockOnHand row exists for this (material, warehouse, status) tuple.
        If missing, stages a base record with rm_soh = 0.00 so balance views compute in 15ms.
        """
        check_query = text("""
            SELECT 1 FROM schema_whrm.view_beginning_soh
            WHERE warehouseid = :warehouse_id
              AND rawmaterialid = :rm_code_id
              AND statusid = :status_id
            LIMIT 1
        """)
        exists = self.db.execute(check_query, {
            "warehouse_id": wh_id,
            "rm_code_id": rm_id,
            "status_id": status_id
        }).fetchone()

        if not exists:
            meta_query = text("""
                SELECT date_computed, recalculation_count 
                FROM schema_whrm.view_beginning_soh 
                ORDER BY recalculation_count DESC 
                LIMIT 1
            """)
            meta_record = self.db.execute(meta_query).mappings().fetchone()

            date_computed = meta_record["date_computed"] if meta_record else None
            recalc_count = meta_record["recalculation_count"] if meta_record else 1

            new_stock = StockOnHand(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=status_id,
                rm_soh=Decimal("0.00"),
                date_computed=date_computed,
                stock_recalculation_count=recalc_count
            )
            self.db.add(new_stock)
            self.db.flush()

    def get_by_id(self, report_id: UUID) -> Optional[TempReceivingReport]:
        """Fetches a single receiving report by primary UUID."""
        return self.db.query(TempReceivingReport).filter(TempReceivingReport.id == report_id).first()

    def create(self, record: TempReceivingReport) -> TempReceivingReport:
        """Stages a new receiving report entry in the active transaction."""
        self.db.add(record)
        self.db.flush()
        return record

    def list_active(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active receiving reports via lightweight row mappings."""
        rows = (
            self.db.query(
                TempReceivingReport.id,
                TempReceivingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.qty_kg,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempReceivingReport.date_computed,
                TempReceivingReport.is_adjusted
            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id)
            .join(Status, TempReceivingReport.status_id == Status.id)
            .outerjoin(User, TempReceivingReport.created_by_id == User.id)
            .filter(
                or_(TempReceivingReport.is_cleared.is_(None), TempReceivingReport.is_cleared.is_(False)),
                or_(TempReceivingReport.is_deleted.is_(None), TempReceivingReport.is_deleted.is_(False))
            )
            .order_by(desc(TempReceivingReport.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_deleted(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted receiving reports for audit recovery."""
        rows = (
            self.db.query(
                TempReceivingReport.id,
                TempReceivingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.qty_kg,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id)
            .join(Status, TempReceivingReport.status_id == Status.id)
            .outerjoin(User, TempReceivingReport.created_by_id == User.id)
            .filter(TempReceivingReport.is_deleted.is_(True))
            .order_by(desc(TempReceivingReport.updated_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_historical(
        self,
        record_id: Optional[UUID] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical receiving records with pagination."""
        query = (
            self.db.query(
                TempReceivingReport.id,
                TempReceivingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.qty_kg,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempReceivingReport.date_computed,
                TempReceivingReport.is_adjusted
            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id)
            .join(Status, TempReceivingReport.status_id == Status.id)
            .outerjoin(User, TempReceivingReport.created_by_id == User.id)
            .filter(
                TempReceivingReport.date_computed.is_not(None),
                or_(TempReceivingReport.is_deleted.is_(None), TempReceivingReport.is_deleted.is_(False))
            )
        )
        if record_id:
            query = query.filter(TempReceivingReport.id == record_id)

        rows = query.order_by(desc(TempReceivingReport.date_computed)).limit(limit).offset(offset).all()
        return [dict(row._mapping) for row in rows]