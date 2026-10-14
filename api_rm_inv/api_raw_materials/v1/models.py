"""
Raw Material Database Entity Model.

Defines the master catalog of chemical ingredients, pigments, additives, 
and warehouse supplies stored in the plant and tracked within schema_whrm.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base
from shared.users.models import User


class RawMaterial(Base):
    """
    Database entity representing unique raw material items and supplies.

    Attributes:
        id: Primary key UUID identifying the material record internally.
        rm_code: Unique alphanumeric code for the material (e.g., 'RM-1045').
        rm_name: Human-friendly display name (e.g., 'Calcium Carbonate Masterbatch').
        type: Classification indicator ('RM' for raw material, 'SUPPLY' for packaging/general items).
        description: Technical specifications or storage notes.
        is_deleted: Soft delete flag preserving audit history and historical transaction balances.
        created_at: UTC timestamp when the material was registered.
        updated_at: UTC timestamp of the most recent modification.
        created_by_id: Foreign key linking to the User who entered the material.
        updated_by_id: Foreign key linking to the User who last updated the material.
        deleted_by_id: Foreign key linking to the User who soft-deleted the material.
    """
    __tablename__ = "tbl_raw_materials"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    rm_code = Column(String(50), nullable=False, unique=True, index=True)
    rm_name = Column(String(150), nullable=True)
    type = Column(
        Enum("RM", "SUPPLY", name="rm_type_enum"),
        nullable=True,
        default="RM"
    )
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
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True
    )

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("tbl_users.id"), nullable=True)

    # Relationships to the shared User model for audit tracking
    created_by = relationship("User", foreign_keys=[created_by_id])
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    deleted_by = relationship("User", foreign_keys=[deleted_by_id])