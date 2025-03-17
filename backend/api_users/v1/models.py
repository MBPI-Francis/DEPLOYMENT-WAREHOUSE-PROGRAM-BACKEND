import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.settings.database import Base  # Assuming Base is imported from your database setup



# Child Model: User
class User(Base):
    __tablename__ = "tbl_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    user_name = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_reguser = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deavtivated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)


    # Relationships for created_by, deactivated_by and updated_by
    created_by = relationship("User", remote_side=[id], foreign_keys=[created_by_id], backref="created_users")
    updated_by = relationship("User", remote_side=[id], foreign_keys=[updated_by_id], backref="updated_users")
    deactivated_by = relationship("User", remote_side=[id], foreign_keys=[deavtivated_by_id], backref="deactivated_users")

