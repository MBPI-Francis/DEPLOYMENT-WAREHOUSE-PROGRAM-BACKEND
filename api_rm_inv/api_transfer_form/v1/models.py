"""
Transfer Form Database Entity Model.

Represents stock movements between physical warehouse locations (e.g., Main Warehouse to Silo),
affecting both the 'transferred_from' (deduction) and 'transferred_to' (addition)
computations inside schema_whrm.view_ending_stocks_balance.
"""

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from shared.users.models import User


class TempTransferForm(Base):
    """
    Database entity for internal warehouse-to-warehouse stock transfers.
    """
    __tablename__ = "tbl_transfer_forms"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_raw_materials.id"), nullable=False)
    from_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=False)
    to_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=False)
    status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=True)

    ref_number = Column(String(50), nullable=False, index=True)
    transfer_date = Column(Date, nullable=False, default=date.today)
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

    # Relationships for audit and display lookups
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id])
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    status = relationship("Status", foreign_keys=[status_id])