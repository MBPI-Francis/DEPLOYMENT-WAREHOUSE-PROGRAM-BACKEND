"""
Data Access Layer (CRUD) for Outgoing Reports (v2).

Queries schema_whrm.view_adjusted_ending_balance to verify available physical stock
before allowing materials to be dispatched out of the warehouse.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func

from core.base import BaseRepository
from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class TempOutgoingReportCRUD(BaseRepository):
    """Repository handling database queries and stock validations for outbound reports."""

    def resolve_raw_material(self, rm_code: str) -> Optional[RawMaterial]:
        """Looks up a material by code, ignoring spaces and case."""
        cleaned = rm_code.replace(" ", "").upper()
        return (
            self.db.query(RawMaterial)
            .filter(func.replace(func.upper(RawMaterial.rm_code), " ", "") == cleaned)
            .first()
        )

    def resolve_warehouse(self, wh_number: str) -> Optional[Warehouse]:
        """Looks up a warehouse by number or name."""
        target = str(wh_number).strip()
        wh = self.db.query(Warehouse).filter(Warehouse.wh_number == target).first()
        if wh:
            return wh
        return self.db.query(Warehouse).filter(Warehouse.wh_name.ilike(f"%{target}%")).first()

    def resolve_status(self, status_name: str) -> Optional[Status]:
        """Looks up a quality status by name."""
        target = status_name.strip().lower()
        return self.db.query(Status).filter(func.lower(Status.name) == target).first()

    def get_available_stock(self, rm_id: UUID, wh_id: UUID, status_id: UUID) -> Decimal:
        """
        Queries schema_whrm.view_adjusted_ending_balance for live inventory balance
        before allowing an outbound dispatch.

        Returns Decimal('0.00') if no stock balance exists.
        """
        stock_query = text("""
            SELECT COALESCE(new_beginning_balance, 0) AS balance
            FROM schema_whrm.view_adjusted_ending_balance
            WHERE rawmaterialid = :rm_id
              AND warehouseid = :wh_id
              AND statusid = :status_id
            LIMIT 1
        """)
        record = self.db.execute(stock_query, {
            "rm_id": rm_id,
            "wh_id": wh_id,
            "status_id": status_id
        }).fetchone()

        if record and record[0] is not None:
            return Decimal(str(record[0]))
        return Decimal("0.00")

    def get_by_id(self, report_id: UUID) -> Optional[TempOutgoingReport]:
        """Fetches a single outgoing report record by UUID."""
        return self.db.query(TempOutgoingReport).filter(TempOutgoingReport.id == report_id).first()

    def create(self, record: TempOutgoingReport) -> TempOutgoingReport:
        """Persists a new outgoing report entry."""
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_active(self) -> List[dict]:
        """Retrieves active, un-cleared outgoing reports with readable joined data."""
        records = (
            self.db.query(
                TempOutgoingReport.id,
                TempOutgoingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_type,
                TempOutgoingReport.outgoing_destination,
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempOutgoingReport.date_computed,
                TempOutgoingReport.is_adjusted
            )
            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .outerjoin(User, TempOutgoingReport.created_by_id == User.id)
            .filter(
                or_(TempOutgoingReport.is_cleared.is_(None), TempOutgoingReport.is_cleared.is_(False)),
                or_(TempOutgoingReport.is_deleted.is_(None), TempOutgoingReport.is_deleted.is_(False))
            )
            .order_by(desc(TempOutgoingReport.created_at))
            .all()
        )
        return [dict(row._mapping) for row in records]

    def list_deleted(self) -> List[dict]:
        """Retrieves soft-deleted outgoing reports for audit recovery."""
        records = (
            self.db.query(
                TempOutgoingReport.id,
                TempOutgoingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_type,
                TempOutgoingReport.outgoing_destination,
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .outerjoin(User, TempOutgoingReport.created_by_id == User.id)
            .filter(TempOutgoingReport.is_deleted.is_(True))
            .order_by(desc(TempOutgoingReport.updated_at))
            .all()
        )
        return [dict(row._mapping) for row in records]

    def list_historical(
        self,
        record_id: Optional[UUID] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        rm_code: Optional[str] = None,
        warehouse_name: Optional[str] = None,
        status_name: Optional[str] = None,
        outgoing_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Retrieves computed historical outgoing records with pagination
        and multi-field filtering. Converts rows to dictionaries for high serialization throughput.
        """
        query = (
            self.db.query(
                TempOutgoingReport.id,
                TempOutgoingReport.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_type,
                TempOutgoingReport.outgoing_destination,
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempOutgoingReport.date_computed,
                TempOutgoingReport.is_adjusted
            )
            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .outerjoin(User, TempOutgoingReport.created_by_id == User.id)
            .filter(
                TempOutgoingReport.date_computed.is_not(None),
                or_(TempOutgoingReport.is_deleted.is_(None), TempOutgoingReport.is_deleted.is_(False))
            )
        )

        if record_id:
            query = query.filter(TempOutgoingReport.id == record_id)

        if date_from and date_to:
            query = query.filter(and_(TempOutgoingReport.outgoing_date >= date_from, TempOutgoingReport.outgoing_date <= date_to))
        elif date_from:
            query = query.filter(TempOutgoingReport.outgoing_date >= date_from)
        elif date_to:
            query = query.filter(TempOutgoingReport.outgoing_date <= date_to)

        if rm_code and rm_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == rm_code.strip())

        if warehouse_name and warehouse_name.strip().lower() != "all":
            query = query.filter(Warehouse.wh_name == warehouse_name.strip())

        if status_name and status_name.strip().lower() != "all":
            query = query.filter(func.lower(Status.name) == status_name.strip().lower())

        if outgoing_type and outgoing_type.strip().lower() != "all":
            query = query.filter(func.upper(TempOutgoingReport.outgoing_type) == outgoing_type.strip().upper())

        records = (
            query
            .order_by(desc(TempOutgoingReport.date_computed), desc(TempOutgoingReport.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]