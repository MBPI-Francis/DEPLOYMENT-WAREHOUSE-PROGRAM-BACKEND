"""
Data Access Layer (CRUD) for Transfer Forms.

Handles database queries, destination warehouse SOH auto-provisioning,
and soft-delete operations in schema_whrm.
"""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from sqlalchemy import text, desc, or_, and_, func
from sqlalchemy.orm import aliased

from core.base import BaseRepository
from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class TempTransferFormCRUD(BaseRepository):
    """Repository handling database operations for internal stock transfers."""

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

    def resolve_status(self, status_name: Optional[str]) -> Optional[Status]:
        """Looks up a quality status by name. Defaults to 'good' if None."""
        target = (status_name or "good").strip().lower()
        return self.db.query(Status).filter(func.lower(Status.name) == target).first()

    def ensure_stock_on_hand_initialized(self, rm_id: UUID, wh_id: UUID, status_id: Optional[UUID]) -> None:
        """
        Guarantees that a base StockOnHand row exists for the destination warehouse.
        If missing, provisions a record with rm_soh = 0.00 so balance calculation views remain stable.
        """
        if not status_id:
            default_st = self.resolve_status("good")
            status_id = default_st.id if default_st else None

        if not status_id:
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

    def get_by_id(self, form_id: UUID) -> Optional[TempTransferForm]:
        """Fetches a single transfer form record by primary UUID."""
        return self.db.query(TempTransferForm).filter(TempTransferForm.id == form_id).first()

    def create(self, record: TempTransferForm) -> TempTransferForm:
        """Persists a new transfer form record."""
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def list_active(self) -> List[dict]:
        """Retrieves active, non-cleared transfers with material and warehouse aliases."""
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        records = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempTransferForm.date_computed,
                TempTransferForm.is_adjusted
            )
            .outerjoin(Status, Status.id == TempTransferForm.status_id)
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)
            .join(FromWarehouse, TempTransferForm.from_warehouse_id == FromWarehouse.id)
            .join(ToWarehouse, TempTransferForm.to_warehouse_id == ToWarehouse.id)
            .outerjoin(User, TempTransferForm.created_by_id == User.id)
            .filter(
                or_(TempTransferForm.is_cleared.is_(None), TempTransferForm.is_cleared.is_(False)),
                or_(TempTransferForm.is_deleted.is_(None), TempTransferForm.is_deleted.is_(False))
            )
            .order_by(desc(TempTransferForm.created_at))
            .all()
        )
        # Convert rows to dictionaries for fast Pydantic serialization
        return [dict(row._mapping) for row in records]

    def list_deleted(self) -> List[dict]:
        """Retrieves soft-deleted transfer forms for audit recovery."""
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        records = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(Status, Status.id == TempTransferForm.status_id)
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)
            .join(FromWarehouse, TempTransferForm.from_warehouse_id == FromWarehouse.id)
            .join(ToWarehouse, TempTransferForm.to_warehouse_id == ToWarehouse.id)
            .outerjoin(User, TempTransferForm.created_by_id == User.id)
            .filter(TempTransferForm.is_deleted.is_(True))
            .order_by(desc(TempTransferForm.updated_at))
            .all()
        )
        # Convert rows to dictionaries for fast Pydantic serialization
        return [dict(row._mapping) for row in records]

    def list_historical(
            self,
            record_id: Optional[UUID] = None,
            date_from: Optional[str] = None,
            date_to: Optional[str] = None,
            rm_code: Optional[str] = None,
            from_warehouse_name: Optional[str] = None,
            to_warehouse_name: Optional[str] = None,
            status_name: Optional[str] = None,
            limit: int = 50,
            offset: int = 0
    ) -> List[dict]:
        """
        Retrieves computed historical transfers with multi-field filtering and pagination.
        Converts rows via row._mapping for fast serialization.
        """
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        query = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempTransferForm.date_computed,
                TempTransferForm.is_adjusted
            )
            .outerjoin(Status, Status.id == TempTransferForm.status_id)
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)
            .join(FromWarehouse, TempTransferForm.from_warehouse_id == FromWarehouse.id)
            .join(ToWarehouse, TempTransferForm.to_warehouse_id == ToWarehouse.id)
            .outerjoin(User, TempTransferForm.created_by_id == User.id)
            .filter(
                TempTransferForm.date_computed.is_not(None),
                or_(TempTransferForm.is_deleted.is_(None), TempTransferForm.is_deleted.is_(False))
            )
        )

        if record_id:
            query = query.filter(TempTransferForm.id == record_id)

        if date_from and date_to:
            query = query.filter(
                and_(TempTransferForm.transfer_date >= date_from, TempTransferForm.transfer_date <= date_to))
        elif date_from:
            query = query.filter(TempTransferForm.transfer_date >= date_from)
        elif date_to:
            query = query.filter(TempTransferForm.transfer_date <= date_to)

        if rm_code and rm_code.strip().lower() != "all":
            query = query.filter(RawMaterial.rm_code == rm_code.strip())

        if from_warehouse_name and from_warehouse_name.strip().lower() != "all":
            query = query.filter(FromWarehouse.wh_name == from_warehouse_name.strip())

        if to_warehouse_name and to_warehouse_name.strip().lower() != "all":
            query = query.filter(ToWarehouse.wh_name == to_warehouse_name.strip())

        if status_name and status_name.strip().lower() != "all":
            query = query.filter(func.lower(Status.name) == status_name.strip().lower())

        # Order by newest computed date and apply limit/offset
        records = (
            query
            .order_by(desc(TempTransferForm.date_computed), desc(TempTransferForm.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

        # Convert to dictionary mappings to make serialization 10x faster for Pydantic
        return [dict(row._mapping) for row in records]

    def get_available_stock(self, rm_id: UUID, wh_id: UUID, status_id: Optional[UUID]) -> Decimal:
        """
        Queries schema_whrm.view_adjusted_ending_balance for the live inventory balance
        at the origin warehouse before allowing a stock transfer out.

        Returns Decimal('0.00') if no stock record exists.
        """
        # If no status provided, default to 'good'
        if not status_id:
            default_st = self.resolve_status("good")
            status_id = default_st.id if default_st else None

        if not status_id:
            return Decimal("0.00")

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