"""
Standalone Password Reset Utility.

Lists all users in schema_whrm.tbl_users and sets a fresh,
properly salted bcrypt password so you can log in immediately.
"""

from core.database import SessionLocal
from core.security import hash_password
from shared.users.models import User


def reset_user_password():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("❌ No users found in schema_whrm.tbl_users.")
            return

        print("\n=======================================================")
        print("  AVAILABLE USERS IN schema_whrm.tbl_users:")
        print("=======================================================")
        for u in users:
            print(f"  • Username: {u.username} | Name: {u.full_name} | Role: {u.role}")
        print("=======================================================\n")

        # 1. Ask for target username
        target_username = input("Enter the username you want to reset: ").strip()
        user = db.query(User).filter(User.username.ilike(target_username)).first()

        if not user:
            print(f"❌ User '{target_username}' not found.")
            return

        # 2. Ask for new plain password
        new_plain_pass = input(f"Enter new password for '{user.username}': ").strip()
        if not new_plain_pass:
            print("❌ Password cannot be empty.")
            return

        # 3. Hash with modern bcrypt and save to PostgreSQL
        user.password = hash_password(new_plain_pass)
        db.commit()

        print(f"\n[✔] SUCCESS: Password for '{user.username}' updated to a secure bcrypt hash!")
        print(f"You can now log in at http://localhost:8000/docs using:")
        print(f"  - Username: {user.username}")
        print(f"  - Password: {new_plain_pass}\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Error updating password: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    reset_user_password()