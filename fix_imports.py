import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test all critical imports
try:
    from core_infra.database import get_db, get_db_session
    print("✅ Database imports OK")
except ImportError as e:
    print(f"❌ Database import error: {e}")

try:
    from api.main_babyshield import app
    print("✅ Main API imports OK")
except ImportError as e:
    print(f"❌ Main API import error: {e}")
    
print("Import check complete")
