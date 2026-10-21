"""
Data Access Layer (CRUD) for Preparation Form Module.

Contains direct SQLAlchemy database queries and writes across:
- schema_whprep: Upstream recipe runs and details.
- schema_whrm: Inventory deduction preparation entries and lookups.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, String

from core.base import BaseRepository
from api_rm_inv.api_preparation_form.v1.models import (
    PrepFormHeader,
    PrepFormRun,
    PrepFormDetail,
    PrepStatus,
    TempPreparationForm
)
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class PrepIntegrationCRUD(BaseRepository):
    """Encapsulates all database operations for both integration and preparation management."""

    # -----------------------------------------------------------------------
    # 1. Traveler Integration Queries (schema_whprep)
    # -----------------------------------------------------------------------

    def get_run_by_any_identifier(
        self,
        prod_lot_no: Optional[str] = None,
        prep_form_no: Optional[str] = None,
        prod_id: Optional[str] = None
    ) -> Optional[PrepFormRun]:
        """Looks up the active preparation run by Lot No, Prep Form No, or Product ID."""
        query = (
            self.db.query(PrepFormRun)
            .join(PrepFormHeader, PrepFormRun.header_id == PrepFormHeader.id)
            .filter(PrepFormHeader.is_active.is_(True))
        )

        if prod_lot_no:
            cleaned_lot = prod_lot_no.strip().strip("'").strip('"').upper()
            return query.filter(func.upper(PrepFormRun.lotno_prod) == cleaned_lot).first()

        if prep_form_no:
            cleaned_form = prep_form_no.strip().strip("'").strip('"')
            return query.filter(func.cast(PrepFormHeader.prep_form_no, String) == cleaned_form).first()

        if prod_id:
            cleaned_prod = prod_id.strip().strip("'").strip('"')
            return query.filter(func.cast(PrepFormRun.prod_id, String) == cleaned_prod).first()

        return None

    def get_details_by_run_id(self, run_id: UUID) -> List[PrepFormDetail]:
        """Fetches recipe line items ordered by sequence number."""
        return (
            self.db.query(PrepFormDetail)
            .filter(PrepFormDetail.run_id == run_id, PrepFormDetail.is_deleted.is_(False))
            .order_by(PrepFormDetail.sequence_no.asc())
            .all()
        )

    def get_prep_status_by_code(self, status_code: str) -> Optional[PrepStatus]:
        """Finds traveler status code (e.g., 'COMPLETED') in schema_whprep."""
        return (
            self.db.query(PrepStatus)
            .filter(func.upper(PrepStatus.status_code) == status_code.upper())
            .first()
        )

    def check_lot_already_deducted(self, prod_lot_no: str) -> bool:
        """Verifies if deductions for this lot already exist in inventory preparation."""
        exists = (
            self.db.query(TempPreparationForm.id)
            .filter(
                func.upper(TempPreparationForm.prod_lot_no) == prod_lot_no.strip().upper(),
                TempPreparationForm.is_deleted.is_(False)
            )
            .first()
        )
        return exists is not None

    # -----------------------------------------------------------------------
    # 2. Universal Identifier Resolvers (schema_whrm)
    # -----------------------------------------------------------------------

    def resolve_raw_material(self, rm_code: str) -> Optional[RawMaterial]:
        """Resolves material code to RawMaterial entity."""
        cleaned = rm_code.replace(" ", "").upper()
        return (
            self.db.query(RawMaterial)
            .filter(func.replace(func.upper(RawMaterial.rm_code), " ", "") == cleaned)
            .first()
        )

    def resolve_warehouse(self, wh_number: str) -> Optional[Warehouse]:
        """Resolves warehouse number (or name) to Warehouse entity."""
        target = str(wh_number).strip()
        wh = self.db.query(Warehouse).filter(Warehouse.wh_number == target).first()
        if wh:
            return wh
        return self.db.query(Warehouse).filter(Warehouse.wh_name.ilike(f"%{target}%")).first()

    def resolve_status(self, status_name: str) -> Optional[Status]:
        """Resolves quality status name to Status entity."""
        return (
            self.db.query(Status)
            .filter(func.lower(Status.name) == status_name.strip().lower())
            .first()
        )

    # -----------------------------------------------------------------------
    # 3. Ledger Management CRUD (schema_whrm.tbl_preparation_forms)
    # -----------------------------------------------------------------------

    def get_preparation_by_id(self, form_id: UUID) -> Optional[TempPreparationForm]:
        """Fetches a single deduction row by primary UUID."""
        return self.db.query(TempPreparationForm).filter(TempPreparationForm.id == form_id).first()

    def create_inventory_deduction(self, record: TempPreparationForm) -> TempPreparationForm:
        """Stages a new deduction record to schema_whrm without committing."""
        self.db.add(record)
        self.db.flush()
        return record

    def list_active_preparation_records(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active, un-cleared preparation deduction records with dictionary mapping."""
        rows = (
            self.db.query(
                TempPreparationForm.id,
                TempPreparationForm.ref_number,
                TempPreparationForm.prod_lot_no,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempPreparationForm.qty_required,
                TempPreparationForm.qty_prepared,
                TempPreparationForm.add_qty,
                TempPreparationForm.qty_return,
                TempPreparationForm.rm_lot_no,
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempPreparationForm.date_computed,
                TempPreparationForm.is_adjusted,
                TempPreparationForm.is_cleared
            )
            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)
            .join(Status, TempPreparationForm.status_id == Status.id)
            .outerjoin(User, TempPreparationForm.created_by_id == User.id)
            .filter(
                or_(TempPreparationForm.is_cleared.is_(None), TempPreparationForm.is_cleared.is_(False)),
                or_(TempPreparationForm.is_deleted.is_(None), TempPreparationForm.is_deleted.is_(False))
            )
            .order_by(desc(TempPreparationForm.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_deleted_preparation_records(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted preparation deduction records for auditing."""
        rows = (
            self.db.query(
                TempPreparationForm.id,
                TempPreparationForm.ref_number,
                TempPreparationForm.prod_lot_no,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempPreparationForm.qty_required,
                TempPreparationForm.qty_prepared,
                TempPreparationForm.add_qty,
                TempPreparationForm.qty_return,
                TempPreparationForm.rm_lot_no,
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempPreparationForm.date_computed,
                TempPreparationForm.is_adjusted,
                TempPreparationForm.is_cleared
            )
            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)
            .join(Status, TempPreparationForm.status_id == Status.id)
            .outerjoin(User, TempPreparationForm.created_by_id == User.id)
            .filter(TempPreparationForm.is_deleted.is_(True))
            .order_by(desc(TempPreparationForm.updated_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_historical_preparation_records(
        self,
        record_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical preparation records with dictionary mapping."""
        query = (
            self.db.query(
                TempPreparationForm.id,
                TempPreparationForm.ref_number,
                TempPreparationForm.prod_lot_no,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                TempPreparationForm.qty_required,
                TempPreparationForm.qty_prepared,
                TempPreparationForm.add_qty,
                TempPreparationForm.qty_return,
                TempPreparationForm.rm_lot_no,
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                TempPreparationForm.date_computed,
                TempPreparationForm.is_adjusted,
                TempPreparationForm.is_cleared
            )
            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)
            .join(Status, TempPreparationForm.status_id == Status.id)
            .outerjoin(User, TempPreparationForm.created_by_id == User.id)
            .filter(
                TempPreparationForm.date_computed.is_not(None),
                or_(TempPreparationForm.is_deleted.is_(None), TempPreparationForm.is_deleted.is_(False))
            )
        )
        if record_id:
            query = query.filter(func.cast(TempPreparationForm.id, String) == record_id.strip())

        rows = query.order_by(desc(TempPreparationForm.date_computed)).limit(limit).offset(offset).all()
        return [dict(row._mapping) for row in rows]