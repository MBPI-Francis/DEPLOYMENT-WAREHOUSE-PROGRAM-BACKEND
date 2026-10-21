"""
Product Kind Database Entity Model.

Represents product classification codes (e.g., Masterbatch 'MB', Dry Color 'DC')
mapped to schema_whrm.tbl_product_kind.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from shared.users.models import User


class ProductKind(Base):
    """
    Database entity for product classifications.

    Attributes:
        id: Primary key string code (e.g., 'MB', 'DC').
        name: Readable description of the classification.
        description: Technical details or notes.
        is_deleted: Soft delete flag.
    """
    __tablename__ = "tbl_product_kind"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(String(10), nullable=False, primary_key=True, unique=True, index=True)
    name = Column(String(80), nullable=False)
    description = Column(String(300), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

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