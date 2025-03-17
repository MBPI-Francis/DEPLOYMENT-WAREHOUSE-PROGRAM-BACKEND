import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup
from backend.api_users.v1.models import User


# Parent Model: Department
class TempNotes(Base):
    __tablename__ = "tbl_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    product_code = Column(String(80), nullable=False)
    lot_number = Column(String(80), nullable=False)
    product_kind_id = Column(String(10),  ForeignKey("tbl_product_kind.id"), nullable=False)
    is_deleted = Column(Boolean, default=False)
    stock_change_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    date_computed = Column(Date, nullable=True)
    is_cleared = Column(Boolean, default=False)


    # Relationships for created_by, updated_by, and deleted_by
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_tempnotes")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_tempnotes")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_tempnotes")
    product_kind = relationship("ProductKind", foreign_keys=[product_kind_id], backref="relationship_tempnotes")




