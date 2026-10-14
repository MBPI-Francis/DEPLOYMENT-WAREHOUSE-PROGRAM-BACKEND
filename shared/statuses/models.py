"""
Shared Inventory Status Model.

Universal quality classification statuses ('good', 'held : reject', etc.)
used across Raw Materials, Finished Goods, and Production.
"""

import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class Status(Base):
    """
    Central database entity for inventory condition statuses.
    """
    __tablename__ = "tbl_status"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    name = Column(String(100), nullable=False, unique=True)