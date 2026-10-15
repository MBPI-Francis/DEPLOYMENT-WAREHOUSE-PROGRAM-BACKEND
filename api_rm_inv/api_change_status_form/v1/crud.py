"""
Data Access Layer (CRUD) for Quality Status Change (Held) Forms.

Queries schema_whrm.view_adjusted_ending_balance to verify available physical stock
before allowing reclassifications, avoiding negative inventory balances.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func
from sqlalchemy.orm import aliased

from core.base import BaseRepository
from api_rm_inv.api_change_status_form.v1.models import TempHeldForm
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class TempHeldFormCRUD(BaseRepository):
    """Repository handling database queries and stock validations for Held forms."""

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
        """Looks up a quality status by exact name (case-insensitive)."""
        target = status_name.strip().lower()
        return self.db.query(Status).filter(func.lower(Status.name) == target).first()

    def get_available_stock(self, rm_id: UUID, wh_id: UUID, status_id: UUID) -> Decimal:
        """
        Queries schema_whrm.view_adjusted_ending_balance for current live inventory balance
        for the given (raw material, warehouse, status) combination.

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

    def get_by_id(self, form_id: UUID) -> Optional[TempHeldForm]:
        """Fetches a single held form record by UUID."""
        return self.db.query(TempHeldForm).filter(TempHeldForm.id == form_id).first()

    def create(self, record: TempHeldForm) -> TempHeldForm:
        """Persists a new status change record."""
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_active(self) -> List[dict]:
        """Retrieves active, un-cleared status changes with joined readable names."""
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        records = (
            self.db.query(
                TempHeldForm.id,
                TempHeldForm.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.qty_kg,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempHeldForm.date_computed,
                TempHeldForm.is_adjusted
            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)
            .join(CurrentStatus, TempHeldForm.current_status_id == CurrentStatus.id)
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)
            .outerjoin(User, TempHeldForm.created_by_id == User.id)
            .filter(
                or_(TempHeldForm.is_cleared.is_(None), TempHeldForm.is_cleared.is_(False)),
                or_(TempHeldForm.is_deleted.is_(None), TempHeldForm.is_deleted.is_(False))
            )
            .order_by(desc(TempHeldForm.created_at))
            .all()
        )
        return [dict(row._mapping) for row in records]

    def list_deleted(self) -> List[dict]:
        """Retrieves soft-deleted status changes for auditing."""
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        records = (
            self.db.query(
                TempHeldForm.id,
                TempHeldForm.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.qty_kg,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)
            .join(CurrentStatus, TempHeldForm.current_status_id == CurrentStatus.id)
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)
            .outerjoin(User, TempHeldForm.created_by_id == User.id)
            .filter(TempHeldForm.is_deleted.is_(True))
            .order_by(desc(TempHeldForm.updated_at))
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
        current_status_name: Optional[str] = None,
        new_status_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        Retrieves computed historical status change records with multi-field filtering
        and pagination. Converts rows to dictionaries for high serialization throughput.
        """
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        query = (
            self.db.query(
                TempHeldForm.id,
                TempHeldForm.ref_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.qty_kg,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempHeldForm.date_computed,
                TempHeldForm.is_adjusted
            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)
            .join(CurrentStatus, TempHeldForm.current_status_id == CurrentStatus.id)
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)
            .outerjoin(User, TempHeldForm.created_by_id == User.id)
            .filter(
                TempHeldForm.date_computed.is_not(None),
                or_(TempHeldForm.is_deleted.is_(None), TempHeldForm.is_deleted.is_(False))
            )
        )

        if record_id:
            query = query.filter(TempHeldForm.id == record_id)

        if date_from and date_to:
            query = query.filter(and_(TempHeldForm.change_status_date >= date_from, TempHeldForm.change_status_date <= date_to))
        elif date_from:
            query = query.filter(TempHeldForm.change_status_date >= date_from)
        elif date_to:
            query = query.filter(TempHeldForm.change_status_date <= date_to)

        if rm_code and rm_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == rm_code.strip())

        if warehouse_name and warehouse_name.strip().lower() != "all":
            query = query.filter(Warehouse.wh_name == warehouse_name.strip())

        if current_status_name and current_status_name.strip().lower() != "all":
            query = query.filter(func.lower(CurrentStatus.name) == current_status_name.strip().lower())

        if new_status_name and new_status_name.strip().lower() != "all":
            query = query.filter(func.lower(NewStatus.name) == new_status_name.strip().lower())

        records = (
            query
            .order_by(desc(TempHeldForm.date_computed), desc(TempHeldForm.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]