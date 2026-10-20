"""
Verification Script for Service Account.
Ensures 'service_production_app' exists in schema_whrm.tbl_users.
"""

import uuid
from core.database import SessionLocal
from core.security import hash_password
from shared.users.models import User

db = SessionLocal()
try:
    username = "service_production_app"
    user = db.query(User).filter(User.username == username).first()

    if not user:
        print(f"⚠️ Service user '{username}' not found. Creating it now...")
        service_user = User(
            id=uuid.uuid4(),
            username=username,
            password=hash_password("system_service_secure_random_pass"),
            role="SERVICE",
            department="PRODUCTION",
            first_name="Production",
            last_name="System"
        )
        db.add(service_user)
        db.commit()
        print(f"✅ Service user '{username}' successfully created!")
    else:
        print(f"✅ Service user '{username}' already exists in database (ID: {user.id}).")
finally:
    db.close()