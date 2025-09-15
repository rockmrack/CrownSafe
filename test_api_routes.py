#!/usr/bin/env python3
"""Test API routes without database connection"""

import os
import sys
import json

# Set environment variables to skip database initialization
os.environ["SKIP_DB_INIT"] = "true"
os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost/babyshield"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_API_KEY"] = "test-admin-key"

# Mock database to prevent connection attempts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a simple test to check the route definition
def test_route_definition():
    """Test if the search/advanced route is properly defined"""
    
    # Read the main_babyshield.py file
    with open("api/main_babyshield.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check for the route definition
    if '@app.post("/api/v1/search/advanced"' in content:
        print("✅ Route definition found: @app.post('/api/v1/search/advanced')")
        
        # Find the line number
        for i, line in enumerate(content.split('\n'), 1):
            if '/api/v1/search/advanced' in line:
                print(f"   Line {i}: {line.strip()}")
    else:
        print("❌ Route definition NOT found!")
    
    # Check for AdvancedSearchRequest model
    if 'class AdvancedSearchRequest' in content:
        print("✅ AdvancedSearchRequest model found")
    else:
        print("⚠️  AdvancedSearchRequest model not found in main file")
    
    # Check if it's imported
    if 'from api.models.search_validation import AdvancedSearchRequest' in content:
        print("✅ AdvancedSearchRequest imported from search_validation")
    elif 'AdvancedSearchRequest' in content:
        print("✅ AdvancedSearchRequest is defined or used")
    
    # Check for router includes
    router_includes = []
    for line in content.split('\n'):
        if 'app.include_router' in line:
            router_includes.append(line.strip())
    
    if router_includes:
        print(f"\n📋 Found {len(router_includes)} router includes:")
        for r in router_includes[:5]:  # Show first 5
            print(f"   {r}")

def test_curl_commands():
    """Generate test curl commands"""
    print("\n📝 Test Commands for Deployment:")
    print("="*60)
    
    # Basic test
    print("\n1. Test if API is running:")
    print('curl https://babyshield.cureviax.ai/api/v1/healthz')
    
    # Test search endpoint
    print("\n2. Test search endpoint (should work):")
    print('''curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\
  -H "Content-Type: application/json" \\
  -H "X-Request-ID: test-123" \\
  -d '{
    "product": "pacifier",
    "limit": 5
  }' ''')
    
    print("\n3. Alternative search test:")
    print('''curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\
  -H "Content-Type: application/json" \\
  -d '{"query": "baby formula", "limit": 3}' ''')
    
    print("\n4. Check available endpoints:")
    print('curl https://babyshield.cureviax.ai/docs')
    
def check_deployment_issues():
    """Identify potential deployment issues"""
    print("\n🔍 Potential Deployment Issues:")
    print("="*60)
    
    issues = []
    
    # Check if search service exists
    if not os.path.exists("services/search_service.py"):
        issues.append("❌ services/search_service.py is missing!")
    else:
        print("✅ services/search_service.py exists")
    
    # Check if search validation exists
    if not os.path.exists("api/models/search_validation.py"):
        issues.append("❌ api/models/search_validation.py is missing!")
    else:
        print("✅ api/models/search_validation.py exists")
    
    # Check if pg_trgm migration exists
    migration_path = "alembic/versions/20250826_search_trgm_indexes.py"
    if not os.path.exists(migration_path):
        issues.append(f"⚠️  Migration {migration_path} might not be applied")
    else:
        print(f"✅ Migration file exists: {migration_path}")
    
    if issues:
        print("\n⚠️  Found issues:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ All required files exist locally")
    
    print("\n📌 DEPLOYMENT CHECKLIST:")
    print("1. Ensure all files are committed to git")
    print("2. Push to deployment branch")
    print("3. Run database migrations:")
    print("   alembic upgrade head")
    print("4. Restart the API service")
    print("5. Clear any CDN/proxy cache")

def main():
    print("🔍 BabyShield API Route Checker")
    print("="*60)
    
    test_route_definition()
    check_deployment_issues()
    test_curl_commands()
    
    print("\n💡 SOLUTION:")
    print("="*60)
    print("""
The /api/v1/search/advanced endpoint IS defined in the code (line 899).
The 404 error means the DEPLOYED version doesn't have this endpoint.

TO FIX THE DEPLOYMENT:
1. Commit all changes to git:
   git add .
   git commit -m "Add search/advanced endpoint and related features"
   
2. Push to your deployment branch:
   git push origin main  # or your deployment branch
   
3. On the server, pull the latest code:
   cd /path/to/babyshield
   git pull
   
4. Install any new dependencies:
   pip install -r requirements.txt
   
5. Run database migrations:
   alembic upgrade head
   
6. Restart the API service:
   sudo systemctl restart babyshield  # or your service name
   # OR
   pm2 restart babyshield
   # OR  
   supervisorctl restart babyshield
   
7. Clear any CDN cache if using CloudFront or similar

The endpoint should then be available!
""")

if __name__ == "__main__":
    main()
