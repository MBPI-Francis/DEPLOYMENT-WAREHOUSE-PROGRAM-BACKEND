"""
Stock on Hand Database Entity Model.

Represents baseline snapshot stock balances in schema_whrm.tbl_stock_on_hand.
Matches PostgreSQL DDL schema with 100% precision.
"""

import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class StockOnHand(Base):
    __tablename__ = "tbl_stock_on_hand"
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
    status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=True)

    rm_soh = Column(Numeric(10, 2), nullable=False, default=0.00)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=True)
    is_imported = Column(Boolean, default=False, nullable=True)

    # In PostgreSQL DDL: timestamp without time zone NOT NULL
    stock_change_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    stock_recalculation_count = Column(Integer, nullable=False, default=1)
    date_computed = Column(Date, nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)

    # NOTE: created_at and updated_at DO NOT EXIST in the PostgreSQL table and are omitted!

    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by_id])
    updated_by_user = relationship("User", foreign_keys=[updated_by_id])
    deleted_by_user = relationship("User", foreign_keys=[deleted_by_id])
    rm_code_rel = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse_rel = relationship("Warehouse", foreign_keys=[warehouse_id])
    status_rel = relationship("Status", foreign_keys=[status_id])

    # -----------------------------------------------------------------------
    # Dynamic Properties matching StockOnHandResponse
    # -----------------------------------------------------------------------

    @property
    def rm_code(self) -> str:
        return self.rm_code_rel.rm_code if self.rm_code_rel else ""

    @property
    def rm_name(self) -> Optional[str]:
        return self.rm_code_rel.rm_name if self.rm_code_rel else None

    @property
    def wh_name(self) -> str:
        return self.warehouse_rel.wh_name if self.warehouse_rel else ""

    @property
    def wh_number(self) -> Optional[str]:
        return str(self.warehouse_rel.wh_number) if self.warehouse_rel else None

    @property
    def status(self) -> str:
        return self.status_rel.name if self.status_rel else ""

    @property
    def created_by(self) -> Optional[str]:
        if self.created_by_user:
            first = self.created_by_user.first_name or ""
            last = self.created_by_user.last_name or ""
            full = f"{first} {last}".strip()
            return full if full else self.created_by_user.username
        return None