"""
Shared Warehouse Entity Model.

Master lookup for storage locations, facility codes, and silos across all modules.
Mapped directly to schema_whrm.tbl_warehouses.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, SmallInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class Warehouse(Base):
    """
    Database entity for physical warehouse storage locations.

    Attributes:
        id: Primary key UUID identifying the warehouse.
        wh_number: Numeric facility code (smallint, e.g. 1, 2, 4).
        wh_name: Readable name of the facility (e.g., 'Main Warehouse', 'Silo A').
        description: Location notes or details.
        is_deleted: Soft delete flag.
    """
    __tablename__ = "tbl_warehouses"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    wh_number = Column(SmallInteger, nullable=False, unique=True, index=True)
    wh_name = Column(String(150), nullable=False, unique=True)
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

    # Audit relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])