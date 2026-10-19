"""
Stock on Hand Database Entity Model.

Represents baseline period snapshots, recalculation counts, and initial balances
feeding schema_whrm.view_beginning_soh and schema_whrm.view_ending_stocks_balance.
"""

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Numeric, UniqueConstraint, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class StockOnHand(Base):
    """
    Database entity for Stock on Hand (SOH) baseline snapshots.

    Tracks recalculation generations (stock_recalculation_count) and frozen beginning balances.
    """
    __tablename__ = "tbl_stock_on_hand"
    __table_args__ = (
        UniqueConstraint(
            'rm_code_id', 'rm_soh', 'warehouse_id', 'stock_change_date', 'status_id',
            name='uix_rm_soh_warehouse_status'
        ),
        {"schema": "schema_whrm", "extend_existing": True}
    )

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

    rm_soh = Column(Numeric(10, 2), nullable=False)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_imported = Column(Boolean, default=False, nullable=False)

    stock_change_date = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    stock_recalculation_count = Column(Integer, nullable=False, default=1, index=True)
    date_computed = Column(Date, nullable=True, index=True)


    created_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)

    # Relationships for display lookups
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    status = relationship("Status", foreign_keys=[status_id])