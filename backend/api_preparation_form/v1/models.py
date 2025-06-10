import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, SmallInteger, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup



# Parent Model: Department
class TempPreparationForm(Base):
    __tablename__ = "tbl_preparation_forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=False)
    status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=True)

    ref_number = Column(String(50), nullable=False, unique=False)
    preparation_date = Column(Date,nullable=False)
    qty_prepared = Column(Numeric(10, 2), nullable=False)
    qty_return = Column(Numeric(10, 2), nullable=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    date_computed = Column(Date, nullable=True)
    is_cleared = Column(Boolean, default=False)
    is_adjusted = Column(Boolean, default=False)


    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_preparation_form_temp")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_preparation_form_temp")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_preparation_form_temp")
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id], backref="rm_preparation_form_temp")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], backref="warehouse_preparation_form_temp")
    status = relationship("Status", foreign_keys=[status_id], backref="status_preparation_form_temp")





