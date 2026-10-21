"""
Data Access Layer (CRUD) for Spillage Adjustment Forms.

Queries schema_whrm.view_adjusted_ending_balance to verify available physical stock
before allowing spillage losses to be written, avoiding negative stock balances.
Strictly free of manual commits and HTTP exceptions.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func

from core.base import BaseRepository
from api_rm_inv.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class AdjustmentFormCRUD(BaseRepository):
    """Repository handling database queries and stock validations for spillage forms."""

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
        before allowing a spillage deduction.

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

    def get_by_id(self, form_id: UUID) -> Optional[SpillageAdjustmentForm]:
        """Fetches a single spillage record by UUID."""
        return self.db.query(SpillageAdjustmentForm).filter(SpillageAdjustmentForm.id == form_id).first()

    def create(self, record: SpillageAdjustmentForm) -> SpillageAdjustmentForm:
        """Stages a new spillage record in the active transaction."""
        self.db.add(record)
        self.db.flush()
        return record

    def list_active(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves active, un-cleared spillage entries with joined readable names and pagination."""
        records = (
            self.db.query(
                SpillageAdjustmentForm.id,
                SpillageAdjustmentForm.ref_number,
                SpillageAdjustmentForm.spillage_form_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.reason,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                SpillageAdjustmentForm.date_computed
            )
            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .outerjoin(User, SpillageAdjustmentForm.created_by_id == User.id)
            .filter(
                or_(SpillageAdjustmentForm.is_cleared.is_(None), SpillageAdjustmentForm.is_cleared.is_(False)),
                or_(SpillageAdjustmentForm.is_deleted.is_(None), SpillageAdjustmentForm.is_deleted.is_(False))
            )
            .order_by(desc(SpillageAdjustmentForm.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]

    def list_deleted(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves soft-deleted spillage records for audit recovery with pagination."""
        records = (
            self.db.query(
                SpillageAdjustmentForm.id,
                SpillageAdjustmentForm.ref_number,
                SpillageAdjustmentForm.spillage_form_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.reason,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .outerjoin(User, SpillageAdjustmentForm.created_by_id == User.id)
            .filter(SpillageAdjustmentForm.is_deleted.is_(True))
            .order_by(desc(SpillageAdjustmentForm.updated_at))
            .limit(limit)
            .offset(offset)
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
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical spillage records with pagination and multi-field filtering."""
        query = (
            self.db.query(
                SpillageAdjustmentForm.id,
                SpillageAdjustmentForm.ref_number,
                SpillageAdjustmentForm.spillage_form_number,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.reason,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                SpillageAdjustmentForm.date_computed
            )
            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .outerjoin(User, SpillageAdjustmentForm.created_by_id == User.id)
            .filter(
                SpillageAdjustmentForm.date_computed.is_not(None),
                or_(SpillageAdjustmentForm.is_deleted.is_(None), SpillageAdjustmentForm.is_deleted.is_(False))
            )
        )

        if record_id:
            query = query.filter(SpillageAdjustmentForm.id == record_id)

        if date_from and date_to:
            query = query.filter(and_(SpillageAdjustmentForm.adjustment_date >= date_from, SpillageAdjustmentForm.adjustment_date <= date_to))
        elif date_from:
            query = query.filter(SpillageAdjustmentForm.adjustment_date >= date_from)
        elif date_to:
            query = query.filter(SpillageAdjustmentForm.adjustment_date <= date_to)

        if rm_code and rm_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == rm_code.strip())

        if warehouse_name and warehouse_name.strip().lower() != "all":
            query = query.filter(Warehouse.wh_name == warehouse_name.strip())

        if status_name and status_name.strip().lower() != "all":
            query = query.filter(func.lower(Status.name) == status_name.strip().lower())

        records = (
            query
            .order_by(desc(SpillageAdjustmentForm.date_computed), desc(SpillageAdjustmentForm.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]