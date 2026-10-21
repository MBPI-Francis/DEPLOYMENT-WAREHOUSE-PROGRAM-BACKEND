"""
Data Access Layer (CRUD) for Supplies Outgoing Reports.

Handles queries and staged writes for general warehouse supplies dispatched out of the plant.
Strictly free of manual commits and HTTP exceptions.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import or_, desc, func

from core.base import BaseRepository
from api_rm_inv.api_supplies_outgoing_report.v1.models import SuppliesOutgoingReport
from api_rm_inv.api_supplies_outgoing_report.v1.schemas import SuppliesOutgoingFormCreate, SuppliesOutgoingFormUpdate
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class SuppliesOutgoingReportCRUD(BaseRepository):
    """Repository handling all database interactions for tbl_supplies_outgoing_reports."""

    def resolve_supply_material(self, rm_code: str) -> Optional[RawMaterial]:
        """Resolves a supply catalog item by its code."""
        cleaned = rm_code.replace(" ", "").upper()
        return (
            self.db.query(RawMaterial)
            .filter(
                func.replace(func.upper(RawMaterial.rm_code), " ", "") == cleaned,
                RawMaterial.type == "SUPPLY"
            )
            .first()
        )

    def resolve_warehouse(self, wh_number: str) -> Optional[Warehouse]:
        """Resolves a warehouse by its facility number or name."""
        target = str(wh_number).strip()
        wh = self.db.query(Warehouse).filter(Warehouse.wh_number == target).first()
        if wh:
            return wh
        return self.db.query(Warehouse).filter(Warehouse.wh_name.ilike(f"%{target}%")).first()

    def resolve_status(self, status_name: str) -> Optional[Status]:
        """Resolves a status by name."""
        return self.db.query(Status).filter(func.lower(Status.name) == status_name.strip().lower()).first()

    def get_by_id(self, report_id: UUID) -> Optional[SuppliesOutgoingReport]:
        """Fetches a single supplies outgoing report by UUID."""
        return self.db.query(SuppliesOutgoingReport).filter(SuppliesOutgoingReport.id == report_id).first()

    def create(self, record: SuppliesOutgoingReport) -> SuppliesOutgoingReport:
        """Stages a new supplies outgoing report entry in the active transaction."""
        self.db.add(record)
        self.db.flush()
        return record

    def list_active(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active, un-cleared supplies outgoing reports using dictionary mappings."""
        rows = (
            self.db.query(
                SuppliesOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                SuppliesOutgoingReport.qty_kg,
                SuppliesOutgoingReport.ref_number,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SuppliesOutgoingReport.outgoing_date,
                SuppliesOutgoingReport.created_at,
                SuppliesOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                SuppliesOutgoingReport.date_computed
            )
            .join(RawMaterial, SuppliesOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, SuppliesOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, SuppliesOutgoingReport.status_id == Status.id)
            .outerjoin(User, SuppliesOutgoingReport.created_by_id == User.id)
            .filter(
                or_(SuppliesOutgoingReport.is_cleared.is_(None), SuppliesOutgoingReport.is_cleared.is_(False)),
                or_(SuppliesOutgoingReport.is_deleted.is_(None), SuppliesOutgoingReport.is_deleted.is_(False))
            )
            .order_by(desc(SuppliesOutgoingReport.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_deleted(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated soft-deleted supplies outgoing reports for audit recovery."""
        rows = (
            self.db.query(
                SuppliesOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                SuppliesOutgoingReport.qty_kg,
                SuppliesOutgoingReport.ref_number,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SuppliesOutgoingReport.outgoing_date,
                SuppliesOutgoingReport.created_at,
                SuppliesOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                SuppliesOutgoingReport.date_computed
            )
            .join(RawMaterial, SuppliesOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, SuppliesOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, SuppliesOutgoingReport.status_id == Status.id)
            .outerjoin(User, SuppliesOutgoingReport.created_by_id == User.id)
            .filter(SuppliesOutgoingReport.is_deleted.is_(True))
            .order_by(desc(SuppliesOutgoingReport.updated_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def list_historical(
        self,
        record_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical supplies reports with pagination."""
        query = (
            self.db.query(
                SuppliesOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                RawMaterial.rm_name,
                SuppliesOutgoingReport.qty_kg,
                SuppliesOutgoingReport.ref_number,
                Warehouse.wh_name,
                Warehouse.wh_number,
                Status.name.label("status"),
                SuppliesOutgoingReport.outgoing_date,
                SuppliesOutgoingReport.created_at,
                SuppliesOutgoingReport.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by"),
                SuppliesOutgoingReport.date_computed,
                SuppliesOutgoingReport.is_adjusted
            )
            .join(RawMaterial, SuppliesOutgoingReport.rm_code_id == RawMaterial.id)
            .join(Warehouse, SuppliesOutgoingReport.warehouse_id == Warehouse.id)
            .join(Status, SuppliesOutgoingReport.status_id == Status.id)
            .outerjoin(User, SuppliesOutgoingReport.created_by_id == User.id)
            .filter(
                SuppliesOutgoingReport.date_computed.is_not(None),
                or_(SuppliesOutgoingReport.is_deleted.is_(None), SuppliesOutgoingReport.is_deleted.is_(False))
            )
        )
        if record_id:
            query = query.filter(SuppliesOutgoingReport.id == record_id)

        rows = query.order_by(desc(SuppliesOutgoingReport.date_computed)).limit(limit).offset(offset).all()
        return [dict(row._mapping) for row in rows]