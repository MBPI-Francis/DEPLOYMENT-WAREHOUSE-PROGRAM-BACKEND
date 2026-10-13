"""
Shared Base Classes for Data Access and Business Logic.

These classes replace the redundant AppService and AppCRUD declarations
previously copied into every module's main.py file.
"""

from sqlalchemy.orm import Session


class BaseRepository:
    """
    Base Data Access Object (Repository).

    Every repository/CRUD class inherits from this to gain direct access
    to the underlying database session for querying and persisting data.
    """

    def __init__(self, db: Session):
        """
        Initializes the repository with an active database session.

        Args:
            db (Session): Active SQLAlchemy session for the current request.
        """
        self.db = db


class BaseService:
    """
    Base Business Service Layer.

    Every service inherits from this class. Services are responsible for:
    - Applying business validation rules.
    - Coordinating multiple repository calls.
    - Handling transactional integrity.
    """

    def __init__(self, db: Session):
        """
        Initializes the service with an active database session.

        Args:
            db (Session): Active SQLAlchemy session for the current request.
        """
        self.db = db