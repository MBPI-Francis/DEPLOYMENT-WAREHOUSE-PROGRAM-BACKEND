"""
Data Access Layer (CRUD) for Form Entries Adjustments.

Handles cross-table atomic updates, SOH provisioning, and joining
all five corrected transaction types in schema_whrm.
Strictly free of manual commits and HTTP exceptions.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func
from sqlalchemy.orm import aliased

from core.base import BaseRepository
from api_rm_inv.api_adjustment_form.v1_form_entries.models import AdjustmentFormParent, AdjustmentFormCorrect
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class AdjustmentFormCRUD(BaseRepository):
    """Encapsulates all database operations for form entry corrections."""

    # -----------------------------------------------------------------------
    # Resolvers & SOH Baseline Provisioner
    # -----------------------------------------------------------------------

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

    def ensure_stock_on_hand_initialized(self, rm_id: UUID, wh_id: UUID, status_id: Optional[UUID]) -> None:
        """
        Guarantees that an initial SOH record exists for the given (material, warehouse, status) tuple
        so calculation views function without errors.
        """
        if not status_id or not wh_id or not rm_id:
            return

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

    # -----------------------------------------------------------------------
    # Stock Availability Checker
    # -----------------------------------------------------------------------

    def get_available_stock(self, rm_id: UUID, wh_id: UUID, status_id: UUID) -> Decimal:
        """Queries schema_whrm.view_adjusted_ending_balance for live inventory balance."""
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

    # -----------------------------------------------------------------------
    # CRUD Operations
    # -----------------------------------------------------------------------

    def get_parent_by_id(self, parent_id: UUID) -> Optional[AdjustmentFormParent]:
        """Fetches an adjustment header by UUID."""
        return self.db.query(AdjustmentFormParent).filter(AdjustmentFormParent.id == parent_id).first()

    def get_child_by_id(self, child_id: UUID) -> Optional[AdjustmentFormCorrect]:
        """Fetches an adjustment line item by UUID."""
        return self.db.query(AdjustmentFormCorrect).filter(AdjustmentFormCorrect.id == child_id).first()

    def get_child_by_parent_id(self, parent_id: UUID) -> Optional[AdjustmentFormCorrect]:
        """Fetches active line item matching parent header UUID."""
        return self.db.query(AdjustmentFormCorrect).filter(
            AdjustmentFormCorrect.adjustment_parent_id == parent_id,
            AdjustmentFormCorrect.is_deleted.is_(False)
        ).first()

    def list_active(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves active, un-cleared form adjustments with joined readable names and pagination."""
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        records = (
            self.db.query(
                AdjustmentFormCorrect.id,
                AdjustmentFormCorrect.adjustment_parent_id,
                AdjustmentFormParent.ref_number,
                AdjustmentFormParent.adjustment_type,
                AdjustmentFormParent.responsible_person,
                AdjustmentFormParent.adjustment_date,
                AdjustmentFormParent.referenced_date,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                AdjustmentFormCorrect.qty_kg,
                AdjustmentFormCorrect.qty_prepared,
                AdjustmentFormCorrect.qty_return,
                Warehouse.wh_name,
                Warehouse.wh_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                Status.name.label("status"),
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                AdjustmentFormCorrect.incorrect_receiving_id,
                AdjustmentFormCorrect.incorrect_outgoing_id,
                AdjustmentFormCorrect.incorrect_preparation_id,
                AdjustmentFormCorrect.incorrect_transfer_id,
                AdjustmentFormCorrect.incorrect_change_status_id,
                AdjustmentFormCorrect.created_at,
                AdjustmentFormCorrect.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                AdjustmentFormCorrect.date_computed
            )
            .join(AdjustmentFormParent, AdjustmentFormCorrect.adjustment_parent_id == AdjustmentFormParent.id)
            .join(RawMaterial, AdjustmentFormCorrect.rm_code_id == RawMaterial.id)
            .outerjoin(Warehouse, AdjustmentFormCorrect.warehouse_id == Warehouse.id)
            .outerjoin(Status, AdjustmentFormCorrect.status_id == Status.id)
            .outerjoin(FromWarehouse, AdjustmentFormCorrect.from_warehouse_id == FromWarehouse.id)
            .outerjoin(ToWarehouse, AdjustmentFormCorrect.to_warehouse_id == ToWarehouse.id)
            .outerjoin(CurrentStatus, AdjustmentFormCorrect.current_status_id == CurrentStatus.id)
            .outerjoin(NewStatus, AdjustmentFormCorrect.new_status_id == NewStatus.id)
            .outerjoin(User, AdjustmentFormCorrect.created_by_id == User.id)
            .filter(
                or_(AdjustmentFormCorrect.is_cleared.is_(None), AdjustmentFormCorrect.is_cleared.is_(False)),
                or_(AdjustmentFormCorrect.is_deleted.is_(None), AdjustmentFormCorrect.is_deleted.is_(False))
            )
            .order_by(desc(AdjustmentFormCorrect.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]

    def list_deleted(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves soft-deleted form adjustments for audit recovery with pagination."""
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        records = (
            self.db.query(
                AdjustmentFormCorrect.id,
                AdjustmentFormCorrect.adjustment_parent_id,
                AdjustmentFormParent.ref_number,
                AdjustmentFormParent.adjustment_type,
                AdjustmentFormParent.responsible_person,
                AdjustmentFormParent.adjustment_date,
                AdjustmentFormParent.referenced_date,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                AdjustmentFormCorrect.qty_kg,
                AdjustmentFormCorrect.qty_prepared,
                AdjustmentFormCorrect.qty_return,
                Warehouse.wh_name,
                Warehouse.wh_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                Status.name.label("status"),
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                AdjustmentFormCorrect.incorrect_receiving_id,
                AdjustmentFormCorrect.incorrect_outgoing_id,
                AdjustmentFormCorrect.incorrect_preparation_id,
                AdjustmentFormCorrect.incorrect_transfer_id,
                AdjustmentFormCorrect.incorrect_change_status_id,
                AdjustmentFormCorrect.created_at,
                AdjustmentFormCorrect.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .join(AdjustmentFormParent, AdjustmentFormCorrect.adjustment_parent_id == AdjustmentFormParent.id)
            .join(RawMaterial, AdjustmentFormCorrect.rm_code_id == RawMaterial.id)
            .outerjoin(Warehouse, AdjustmentFormCorrect.warehouse_id == Warehouse.id)
            .outerjoin(Status, AdjustmentFormCorrect.status_id == Status.id)
            .outerjoin(FromWarehouse, AdjustmentFormCorrect.from_warehouse_id == FromWarehouse.id)
            .outerjoin(ToWarehouse, AdjustmentFormCorrect.to_warehouse_id == ToWarehouse.id)
            .outerjoin(CurrentStatus, AdjustmentFormCorrect.current_status_id == CurrentStatus.id)
            .outerjoin(NewStatus, AdjustmentFormCorrect.new_status_id == NewStatus.id)
            .outerjoin(User, AdjustmentFormCorrect.created_by_id == User.id)
            .filter(AdjustmentFormCorrect.is_deleted.is_(True))
            .order_by(desc(AdjustmentFormCorrect.updated_at))
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
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical adjustment records with pagination and multi-field filtering."""
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        query = (
            self.db.query(
                AdjustmentFormCorrect.id,
                AdjustmentFormCorrect.adjustment_parent_id,
                AdjustmentFormParent.ref_number,
                AdjustmentFormParent.adjustment_type,
                AdjustmentFormParent.responsible_person,
                AdjustmentFormParent.adjustment_date,
                AdjustmentFormParent.referenced_date,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                AdjustmentFormCorrect.qty_kg,
                AdjustmentFormCorrect.qty_prepared,
                AdjustmentFormCorrect.qty_return,
                Warehouse.wh_name,
                Warehouse.wh_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                Status.name.label("status"),
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                AdjustmentFormCorrect.incorrect_receiving_id,
                AdjustmentFormCorrect.incorrect_outgoing_id,
                AdjustmentFormCorrect.incorrect_preparation_id,
                AdjustmentFormCorrect.incorrect_transfer_id,
                AdjustmentFormCorrect.incorrect_change_status_id,
                AdjustmentFormCorrect.created_at,
                AdjustmentFormCorrect.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                AdjustmentFormCorrect.date_computed
            )
            .join(AdjustmentFormParent, AdjustmentFormCorrect.adjustment_parent_id == AdjustmentFormParent.id)
            .join(RawMaterial, AdjustmentFormCorrect.rm_code_id == RawMaterial.id)
            .outerjoin(Warehouse, AdjustmentFormCorrect.warehouse_id == Warehouse.id)
            .outerjoin(Status, AdjustmentFormCorrect.status_id == Status.id)
            .outerjoin(FromWarehouse, AdjustmentFormCorrect.from_warehouse_id == FromWarehouse.id)
            .outerjoin(ToWarehouse, AdjustmentFormCorrect.to_warehouse_id == ToWarehouse.id)
            .outerjoin(CurrentStatus, AdjustmentFormCorrect.current_status_id == CurrentStatus.id)
            .outerjoin(NewStatus, AdjustmentFormCorrect.new_status_id == NewStatus.id)
            .outerjoin(User, AdjustmentFormCorrect.created_by_id == User.id)
            .filter(
                AdjustmentFormCorrect.date_computed.is_not(None),
                or_(AdjustmentFormCorrect.is_deleted.is_(None), AdjustmentFormCorrect.is_deleted.is_(False))
            )
        )

        if record_id:
            query = query.filter(AdjustmentFormCorrect.id == record_id)

        if date_from and date_to:
            query = query.filter(and_(AdjustmentFormParent.adjustment_date >= date_from, AdjustmentFormParent.adjustment_date <= date_to))
        elif date_from:
            query = query.filter(AdjustmentFormParent.adjustment_date >= date_from)
        elif date_to:
            query = query.filter(AdjustmentFormParent.adjustment_date <= date_to)

        if rm_code and rm_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == rm_code.strip())

        records = (
            query
            .order_by(desc(AdjustmentFormCorrect.date_computed), desc(AdjustmentFormCorrect.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in records]