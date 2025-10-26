"""
Run Alembic migration programmatically to work around file locking issues.
"""

import os
import sys
from alembic.config import Config
from alembic import command


def run_migration():
    # Set up paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_dir = os.path.join(base_dir, "db")
    alembic_ini = os.path.join(db_dir, "alembic.ini")

    # Set database URL
    db_path = os.path.join(db_dir, "babyshield_dev.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    print(f"Database path: {db_path}")
    print(f"Alembic config: {alembic_ini}")
    print(f"DATABASE_URL: {os.environ['DATABASE_URL']}")

    # Change to db directory
    original_dir = os.getcwd()
    os.chdir(db_dir)

    try:
        # Create Alembic config
        alembic_cfg = Config(alembic_ini)

        # Show current revision
        print("\nCurrent revision:")
        command.current(alembic_cfg)

        # Run upgrade
        print("\nRunning upgrade to head...")
        command.upgrade(alembic_cfg, "head")

        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    run_migration()
