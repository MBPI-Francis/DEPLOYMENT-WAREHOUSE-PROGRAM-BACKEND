"""
Database Entity Model for Quality Status Change (Held) Forms.

Represents material quality reclassifications in schema_whrm.tbl_change_status_forms.
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


class TempHeldForm(Base):
    __tablename__ = "tbl_change_status_forms"
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
    current_status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=False)
    new_status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=False)

    ref_number = Column(String(50), nullable=False, index=True)
    change_status_date = Column(Date, nullable=False, default=date.today)
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

    # Clean relationships (Named cleanly to prevent property name collisions)
    created_by_user = relationship("User", foreign_keys=[created_by_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_id])
    deleted_by_user = relationship("User", foreign_keys=[deleted_by_id])
    rm_code_rel = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse_rel = relationship("Warehouse", foreign_keys=[warehouse_id])
    current_status_rel = relationship("Status", foreign_keys=[current_status_id])
    new_status_rel = relationship("Status", foreign_keys=[new_status_id])

    # -----------------------------------------------------------------------
    # Dynamic Properties matching TempHeldFormResponse
    # -----------------------------------------------------------------------

    @property
    def raw_material(self) -> str:
        """Returns the natural material code string (e.g. 'RM-1001')."""
        return self.rm_code_rel.rm_code if self.rm_code_rel else ""

    @property
    def rm_name(self) -> Optional[str]:
        """Returns the friendly material name."""
        return self.rm_code_rel.rm_name if self.rm_code_rel else None

    @property
    def wh_name(self) -> str:
        """Returns the readable warehouse facility name (e.g. 'Warehouse 1')."""
        return self.warehouse_rel.wh_name if self.warehouse_rel else ""

    @property
    def wh_number(self) -> Optional[str]:
        """Returns the warehouse facility number."""
        return str(self.warehouse_rel.wh_number) if self.warehouse_rel else None

    @property
    def current_status(self) -> str:
        """Returns the origin quality status name string (e.g. 'held : contaminated')."""
        return self.current_status_rel.name if self.current_status_rel else ""

    @property
    def new_status(self) -> str:
        """Returns the new quality status name string (e.g. 'good')."""
        return self.new_status_rel.name if self.new_status_rel else ""

    @property
    def created_by(self) -> Optional[str]:
        """Returns the creator's full name string."""
        if self.created_by_user:
            first = self.created_by_user.first_name or ""
            last = self.created_by_user.last_name or ""
            full = f"{first} {last}".strip()
            return full if full else self.created_by_user.username
        return None