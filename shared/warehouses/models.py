"""
Shared Warehouse Entity Model.

Master lookup for storage locations, facility codes, and silos across all modules.
Mapped directly to schema_whrm.tbl_warehouses.
"""

import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class Warehouse(Base):
    """
    Database entity for physical warehouse storage locations.

    Attributes:
        id: Primary key UUID identifying the warehouse.
        wh_name: Readable name of the facility (e.g., 'Main Warehouse', 'Silo A').
        wh_number: Facility code or tracking number (e.g., '1', '2', 'WH-01').
    """
    __tablename__ = "tbl_warehouses"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    wh_name = Column(String(150), nullable=False, unique=True)
    wh_number = Column(String(50), nullable=True)