"""
Shared Master User Entity Model.

Directly matches schema_whrm.tbl_users (or public.tbl_users),
providing company-wide user authentication and identity across all modules.
"""

import uuid
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID, ENUM
from core.database import Base


class User(Base):
    """
    Master User Entity matching tbl_users.

    Attributes:
        id: Primary key UUID identifying the user.
        username: Unique login account name.
        password: Stored bcrypt hashed password.
        workstation_name: Terminal identifier where the user logged in.
        role: Existing PostgreSQL enum ('userrole').
        department: Existing PostgreSQL enum ('department').
        first_name: Given name.
        last_name: Family surname.
    """
    __tablename__ = "tbl_users"
    __table_args__ = {"schema": "schema_whrm", "extend_existing": True}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        index=True
    )
    username = Column(String(50), nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)  # Stores bcrypt hash
    workstation_name = Column(String(40), nullable=True)

    # Use String here so SQLAlchemy accepts any value from Postgres enums without LookupError
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)

    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)

    @property
    def full_name(self) -> str:
        """Returns readable full name for display on desktop screens."""
        return f"{self.first_name} {self.last_name}".strip()