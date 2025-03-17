import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup
from backend.api_users.v1.models import User


# Parent Model: Department
class RawMaterial(Base):
    __tablename__ = "tbl_raw_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    rm_code = Column(String(50), nullable=False, unique=True)
    rm_name = Column(String(150), nullable=True)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)



    # Relationships for created_by, updated_by, and deleted_by
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_rawmaterial")
    updated_by = relationship("User", foreign_keys=[updated_by_id], backref="updated_rawmaterial")
    deleted_by = relationship("User", foreign_keys=[deleted_by_id], backref="deleted_rawmaterial")




