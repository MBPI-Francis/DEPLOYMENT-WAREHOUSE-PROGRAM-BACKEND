import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup
from backend.api_users.v1.models import User


# Parent Model: Department
class ProductKind(Base):
    __tablename__ = "tbl_product_kind"

    id = Column(String(10), nullable=False, primary_key=True, unique=True, index=True)
    name = Column(String(80), nullable=False)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)


    # Relationships for created_by, updated_by, and deleted_by
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_productkind")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_productkind")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_productkind")



