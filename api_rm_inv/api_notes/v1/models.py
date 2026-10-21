"""
Database Entity Model for Warehouse Notepad / Notes.

Tracks batch notes, adjustments, and lot memos in schema_whrm.tbl_notes.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from shared.users.models import User
from api_rm_inv.api_product_kinds.v1.models import ProductKind


class TempNotes(Base):
    __tablename__ = "tbl_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, index=True)
    product_code = Column(String(80), nullable=False, index=True)
    lot_number = Column(String(80), nullable=False, index=True)
    product_kind_id = Column(String(50), ForeignKey("tbl_product_kind.id"), nullable=False)
    stock_change_date = Column(Date, nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    date_computed = Column(Date, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])
    product_kind = relationship("ProductKind", foreign_keys=[product_kind_id])