"""
Outgoing Report Database Entity Model.

Represents outbound raw material and supply dispatches (sales, disposal, tolling, shipment)
serving as the primary outbound inventory deduction ledger in schema_whrm.
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


class TempOutgoingReport(Base):
    """
    Database entity for Outgoing Reports.

    Every active row in this table deducts material stock from the specified
    warehouse in schema_whrm.view_ending_stocks_balance.
    """
    __tablename__ = "tbl_outgoing_reports"
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
    outgoing_type = Column(String(50), nullable=False, default="RM")  # 'RM' or 'SUPPLY'
    outgoing_destination = Column(String(200), nullable=True)

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

    # Relationships for audit display
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    status = relationship("Status", foreign_keys=[status_id])