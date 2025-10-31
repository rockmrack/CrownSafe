# scripts/seed_alpha_users.py

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core_infra.auth.auth_manager import (  # noqa: E402
    create_user,
)  # Should be your user creation utility

from core_infra.database import Role, User, create_tables, get_db_session  # noqa: E402

logging.basicConfig(level=logging.INFO)


def seed_users():
    print("\n--- Seeding Alpha Users and Roles ---")
    create_tables()  # Ensure tables exist

    with get_db_session() as db:
        # Create roles if they don't exist
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if not admin_role:
            admin_role = Role(name="admin", description="Administrator with full access.")
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)

        user_role = db.query(Role).filter(Role.name == "user").first()
        if not user_role:
            user_role = Role(name="user", description="Standard user.")
            db.add(user_role)
            db.commit()
            db.refresh(user_role)

        # Create a default admin user
        admin_email = "admin@babyshield.com"
        if not db.query(User).filter(User.email == admin_email).first():
            create_user(db, email=admin_email, password="adminpassword", role_id=admin_role.id)
            print(f"   ✔ Created admin user: {admin_email}")
        else:
            print(f"   ✔ Admin user already exists: {admin_email}")

        # Create 9 test users
        for i in range(1, 10):
            user_email = f"testuser{i}@babyshield.com"
            if not db.query(User).filter(User.email == user_email).first():
                create_user(db, email=user_email, password="password", role_id=user_role.id)
                print(f"   ✔ Created test user: {user_email}")
            else:
                print(f"   ✔ Test user already exists: {user_email}")

    print("\n--- Seeding complete! ---")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    seed_users()
