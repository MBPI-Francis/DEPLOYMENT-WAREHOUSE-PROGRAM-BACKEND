# backend/api_preparation_form/v1/main.py

from sqlalchemy.orm import Session

class DBSessionMixin:
    def __init__(self, db: Session):
        self.db = db


class AppService(DBSessionMixin):
    pass


class AppCRUD(DBSessionMixin):
    pass