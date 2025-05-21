import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup
from backend.api_users.v1.models import User


# Parent Model: Department
class AdjustmentFormParent(Base):
    __tablename__ = "tbl_adjustment_parent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    # Metadata
    responsible_person = Column(String(30),
                             nullable=False)
    adjustment_type = Column(String(20),
                             nullable=False)  # e.g., "System Entry Error or Paper Form Error"
    ref_number = Column(String(50), nullable=False)
    adjustment_date = Column(Date, nullable=False)
    referenced_date = Column(Date, nullable=False)




class AdjustmentFormCorrect(Base):
    __tablename__ = "tbl_adjustment_correct"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)

    # FORM IDS
    incorrect_preparation_id = Column(UUID(as_uuid=True), ForeignKey("tbl_preparation_forms.id"), nullable=True)
    incorrect_receiving_id = Column(UUID(as_uuid=True), ForeignKey("tbl_receiving_reports.id"), nullable=True)
    incorrect_outgoing_id = Column(UUID(as_uuid=True), ForeignKey("tbl_outgoing_reports.id"), nullable=True)
    incorrect_transfer_id = Column(UUID(as_uuid=True), ForeignKey("tbl_transfer_forms.id"), nullable=True)
    incorrect_change_status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_held_forms.id"), nullable=True)

    # Common references
    adjustment_parent_id = Column(UUID(as_uuid=True), ForeignKey("tbl_adjustment_parent.id"), nullable=False)
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=True)
    from_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=True)
    to_warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=True)

    current_status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=True)
    new_status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=True)
    status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=True)

    qty = Column(Numeric(10, 2), nullable=True)
    qty_prepared = Column(Numeric(10, 2), nullable=True)
    qty_returned = Column(Numeric(10, 2), nullable=True)

    is_deleted = Column(Boolean, default=False)
    is_cleared = Column(Boolean, default=False)
    date_computed = Column(Date, nullable=True)

    # Audit trail
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_adjustments")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_adjustments")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_adjustments")

    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id], backref="adjustments")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], backref="warehouse_adjustments")
    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id],
                                  backref="from_warehouse_adjustments")
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id], backref="to_warehouse_adjustments")

    current_status = relationship("Status", foreign_keys=[current_status_id], backref="current_status_adjustments")
    new_status = relationship("Status", foreign_keys=[new_status_id], backref="new_status_adjustments")
    status = relationship("Status", foreign_keys=[status_id], backref="status_adjustments")

    incorrect_preparation = relationship("TempPreparationForm", foreign_keys=[incorrect_preparation_id], backref="preparation_adjustments")
    incorrect_receiving = relationship("TempReceivingReport", foreign_keys=[incorrect_receiving_id], backref="receiving_adjustments")
    incorrect_outgoing = relationship("TempOutgoingReport", foreign_keys=[incorrect_outgoing_id], backref="outgoing_adjustments")
    incorrect_transfer = relationship("TempTransferForm", foreign_keys=[incorrect_transfer_id], backref="transfer_adjustments")
    incorrect_change_status = relationship("TempHeldForm", foreign_keys=[incorrect_change_status_id], backref="change_status_adjustments")
    adjustment_parent = relationship("AdjustmentFormParent", foreign_keys=[adjustment_parent_id],
                                           backref="parent_adjustments")



