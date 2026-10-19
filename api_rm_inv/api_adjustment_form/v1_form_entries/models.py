"""
Form Entries Adjustment Database Entity Models.

Provides the two-sided historical correction ledger:
- AdjustmentFormParent: Stores header metadata (reason, type, ref number, dates).
- AdjustmentFormCorrect: Stores the corrected line values linked to the original incorrect form,
  feeding directly into schema_whrm.view_adjusted_ending_balance.
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
from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_preparation_form.v1.models import TempPreparationForm
from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
from api_rm_inv.api_change_status_form.v1.models import TempHeldForm


class AdjustmentFormParent(Base):
    """
    Header entity for form entry corrections.
    Matches schema_whrm.tbl_adjustment_parent.
    """
    __tablename__ = "tbl_adjustment_parent"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    ref_number = Column(String(50), nullable=False, index=True)
    adjustment_type = Column(String(50), nullable=False)  # e.g., 'System Entry Error', 'Form Correction'
    responsible_person = Column(String(100), nullable=True)
    adjustment_date = Column(Date, nullable=False, default=date.today)
    referenced_date = Column(Date, nullable=False, default=date.today)

    # One-to-One relationship to corrected child line (Audit dates exist on the child table)
    adjustment_child = relationship(
        "AdjustmentFormCorrect",
        back_populates="adjustment_parent",
        uselist=False,
        cascade="all, delete-orphan"
    )


class AdjustmentFormCorrect(Base):
    """
    Line item entity holding the replacement (correct) values and referencing the incorrect original form.
    """
    __tablename__ = "tbl_adjustment_correct"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    adjustment_parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schema_whrm.tbl_adjustment_parent.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Foreign keys to the original incorrect forms
    incorrect_receiving_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_receiving_reports.id"), nullable=True)
    incorrect_outgoing_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_outgoing_reports.id"), nullable=True)
    incorrect_preparation_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_preparation_forms.id"), nullable=True)
    incorrect_transfer_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_transfer_forms.id"), nullable=True)
    incorrect_change_status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_held_forms.id"), nullable=True)

    # Corrected attributes
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=True)
    from_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=True)
    to_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=True)

    status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=True)
    current_status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=True)
    new_status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=True)

    qty_kg = Column(Numeric(10, 2), nullable=True)
    qty_prepared = Column(Numeric(10, 2), nullable=True)
    qty_return = Column(Numeric(10, 2), nullable=True)

    is_deleted = Column(Boolean, default=False, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    date_computed = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)

    # Relationships
    adjustment_parent = relationship("AdjustmentFormParent", back_populates="adjustment_child")
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    status = relationship("Status", foreign_keys=[status_id])
    current_status = relationship("Status", foreign_keys=[current_status_id])
    new_status = relationship("Status", foreign_keys=[new_status_id])

    incorrect_receiving = relationship("TempReceivingReport", foreign_keys=[incorrect_receiving_id])
    incorrect_outgoing = relationship("TempOutgoingReport", foreign_keys=[incorrect_outgoing_id])
    incorrect_preparation = relationship("TempPreparationForm", foreign_keys=[incorrect_preparation_id])
    incorrect_transfer = relationship("TempTransferForm", foreign_keys=[incorrect_transfer_id])
    incorrect_change_status = relationship("TempHeldForm", foreign_keys=[incorrect_change_status_id])