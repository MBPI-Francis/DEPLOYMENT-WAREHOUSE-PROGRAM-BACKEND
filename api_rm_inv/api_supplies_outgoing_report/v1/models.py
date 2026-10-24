"""
Database Entity Model for Supplies Outgoing Reports.

Tracks general supplies dispatched out of the plant in schema_whrm.tbl_supplies_outgoing_reports.
"""

import uuid
from datetime import datetime, timezone, date
from typing import Optional
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class SuppliesOutgoingReport(Base):
    __tablename__ = "tbl_supplies_outgoing_reports"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=False)
    status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=False)

    ref_number = Column(String(50), nullable=False, index=True)
    outgoing_date = Column(Date, nullable=False, default=date.today)
    qty_kg = Column(Numeric(10, 2), nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    is_adjusted = Column(Boolean, default=False, nullable=False)
    date_computed = Column(Date, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)

    # Relationships (named cleanly to prevent collision with properties)
    created_by_user = relationship("User", foreign_keys=[created_by_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_id])
    deleted_by_user = relationship("User", foreign_keys=[deleted_by_id])
    rm_code_rel = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse_rel = relationship("Warehouse", foreign_keys=[warehouse_id])
    status_rel = relationship("Status", foreign_keys=[status_id])

    # -----------------------------------------------------------------------
    # Dynamic Properties matching SuppliesOutgoingFormResponse
    # -----------------------------------------------------------------------

    @property
    def raw_material(self) -> str:
        """Returns the natural material code string (e.g. 'SUP-1001')."""
        return self.rm_code_rel.rm_code if self.rm_code_rel else ""

    @property
    def rm_name(self) -> Optional[str]:
        """Returns friendly supply material name."""
        return self.rm_code_rel.rm_name if self.rm_code_rel else None

    @property
    def wh_name(self) -> str:
        """Returns readable warehouse name string (e.g. 'Warehouse 1')."""
        return self.warehouse_rel.wh_name if self.warehouse_rel else ""

    @property
    def wh_number(self) -> Optional[str]:
        """Returns warehouse facility number string."""
        return str(self.warehouse_rel.wh_number) if self.warehouse_rel else None

    @property
    def status(self) -> str:
        """Returns quality status name string (e.g. 'good')."""
        return self.status_rel.name if self.status_rel else ""

    @property
    def created_by(self) -> Optional[str]:
        """Returns creator's full name string."""
        if self.created_by_user:
            first = self.created_by_user.first_name or ""
            last = self.created_by_user.last_name or ""
            full = f"{first} {last}".strip()
            return full if full else self.created_by_user.username
        return None