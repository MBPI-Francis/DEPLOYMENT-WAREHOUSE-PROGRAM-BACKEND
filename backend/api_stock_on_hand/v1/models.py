import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Numeric, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup
from backend.api_users.v1.models import User


# Parent Model: Department
class StockOnHand(Base):
    __tablename__ = "tbl_stock_on_hand"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("tbl_warehouses.id"), nullable=False)

    status_id = Column(UUID(as_uuid=True), ForeignKey("tbl_status.id"), nullable=True)
    rm_soh = Column(Numeric(10, 2), nullable=False)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False)
    is_imported = Column(Boolean, default=False)
    stock_change_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    date_computed = Column(Date, nullable=True)

    # Relationships for created_by, updated_by, and deleted_by
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_soh")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_soh")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_soh")
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id], backref="rm_soh")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id], backref="warehouse_soh")
    status = relationship("Status", foreign_keys=[status_id], backref="status_soh")


   # Composite Unique Constraint
    __table_args__ = (
        UniqueConstraint('rm_code_id', 'rm_soh', 'warehouse_id', 'stock_change_date', 'status_id', name='uix_rm_soh_warehouse_status'),
    )


