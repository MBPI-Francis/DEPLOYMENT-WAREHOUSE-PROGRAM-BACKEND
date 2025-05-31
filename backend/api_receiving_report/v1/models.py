import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, SmallInteger, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup


# Parent Model: Department
class TempReceivingReport(Base):
    __tablename__ = "tbl_receiving_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=False)
    status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=False)

    ref_number = Column(String(50), nullable=False, unique=False)
    receiving_date = Column(Date,nullable=False)
    qty_kg = Column(Numeric(10, 2), nullable=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    date_computed = Column(Date, nullable=True)
    is_cleared = Column(Boolean, default=False)


    # Relationships for created_by, updated_by, and deleted_by
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_receiving_report")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_receiving_report")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_receiving_report")
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id], backref="rm_receiving_report")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], backref="warehouse_receiving_report")
    status = relationship("Status", foreign_keys=[status_id], backref="status_receiving_report")



