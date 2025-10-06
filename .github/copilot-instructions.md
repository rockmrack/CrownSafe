# Copilot Instructions for BabyShield Backend

This file provides guidance to GitHub Copilot when working on the BabyShield backend repository.

## Repository Overview

**BabyShield Backend** is a production-ready FastAPI application providing comprehensive baby product safety monitoring across 39 international regulatory agencies. The application serves as the backend for both mobile and web platforms, handling product recalls, barcode scanning, visual recognition, and user account management.

### Key Technologies
- **Framework**: FastAPI 0.104.1 with Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy 2.0.23 and Alembic for migrations
- **Authentication**: JWT tokens with python-jose and passlib
- **Cloud Services**: AWS (boto3), Google Cloud Vision, Firebase Admin
- **Testing**: pytest with 80%+ coverage target, Schemathesis for API contract testing
- **CI/CD**: GitHub Actions with comprehensive smoke, unit, integration, and security tests

### Architecture
- **API Layer**: `api/` - FastAPI endpoints organized by feature
- **Core Infrastructure**: `core_infra/` - Database, caching, and shared services
- **Agents**: `agents/` - Intelligent agents for planning and routing
- **Workers**: `workers/` - Background task processing with Celery
- **Tests**: `tests/` - Comprehensive test suite with pytest

## Development Environment Setup

```bash
# Clone and install dependencies
git clone https://github.com/BabyShield/babyshield-backend.git
cd babyshield-backend

# Install Python dependencies
pip install -r config/requirements/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your local configuration

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn api.main_babyshield:app --reload --port 8001
```

## Coding Standards

### Python Style
- Follow **PEP 8** strictly
- Use **Black** for formatting (line length: 100)
- Use **Ruff** for linting
- Add **type hints** to all function parameters and return values
- Write **docstrings** for all public functions and classes

### Code Quality Rules
- Keep functions small and focused (max ~50 lines)
- Avoid deeply nested code (max 3-4 levels)
- Use descriptive variable and function names
- Prefer explicit over implicit
- Handle errors gracefully with appropriate error messages

### Import Organization
```python
# Standard library imports
import os
from typing import Optional, List, Dict

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Local imports
from api.auth_endpoints import get_current_user
from core_infra.database import get_db
from api.models import User
```

## Common Patterns

### FastAPI Endpoints
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

router = APIRouter(prefix="/api/v1", tags=["feature"])

@router.get("/items", response_model=List[ItemResponse])
async def list_items(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all items for the current user.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of items
    """
    items = db.query(Item).filter(Item.user_id == current_user.id).offset(skip).limit(limit).all()
    return items
```

### Error Handling
```python
# Use appropriate HTTP status codes
if not item:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Item with id {item_id} not found"
    )

# Use try-except for database operations
try:
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
except Exception as e:
    db.rollback()
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create item"
    )
```

### Database Models
```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="items")
```

## Testing Guidelines

### Test Structure
- Place tests in `tests/` directory mirroring the application structure
- Use descriptive test names: `test_<feature>_<scenario>_<expected_result>`
- Follow AAA pattern: Arrange, Act, Assert

### Test Markers
```python
import pytest

@pytest.mark.unit
def test_create_user_success():
    """Test user creation with valid data."""
    # Arrange
    user_data = {"username": "test", "email": "test@example.com"}
    
    # Act
    result = create_user(**user_data)
    
    # Assert
    assert result["username"] == "test"
    assert "id" in result

@pytest.mark.integration
def test_api_endpoint_integration():
    """Integration test for API endpoint."""
    # Test implementation
    pass
```

### Running Tests
```bash
# Run all tests
pytest

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m smoke         # Smoke tests only

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_api_routes.py
```

## Database Migrations

### Creating Migrations
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new field to users table"

# Create empty migration for manual changes
alembic revision -m "Custom data migration"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Migration Best Practices
- Always review auto-generated migrations before committing
- Never modify existing migrations that have been deployed
- Test migrations on a copy of production data before deployment
- Include both `upgrade()` and `downgrade()` functions
- Add proper indexes for foreign keys and frequently queried columns

## Security Considerations

### Never Commit
- ❌ Database files (*.db, *.sqlite)
- ❌ API keys and secrets
- ❌ `.env` files with real credentials
- ❌ Private keys or certificates
- ❌ User data or PII

### Always Do
- ✅ Use environment variables for secrets
- ✅ Validate and sanitize all user inputs
- ✅ Use parameterized queries (SQLAlchemy ORM handles this)
- ✅ Implement rate limiting on authentication endpoints
- ✅ Hash passwords with bcrypt (never store plain text)
- ✅ Use HTTPS in production
- ✅ Keep dependencies updated

### Authentication
```python
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed_password = pwd_context.hash(plain_password)

# Verify password
is_valid = pwd_context.verify(plain_password, hashed_password)

# Create JWT token
token = jwt.encode(
    {"sub": user.id, "exp": datetime.utcnow() + timedelta(days=7)},
    SECRET_KEY,
    algorithm="HS256"
)
```

## CI/CD and Deployment

### Dockerfile Standards
- **Development**: Use `Dockerfile` (includes dev dependencies)
- **Production**: Use `Dockerfile.final` (optimized, minimal)
- **Never** create additional Dockerfiles (e.g., in `api/` directory)

### GitHub Actions Workflows
- **CI Smoke**: `ci.yml` - Basic smoke tests on every push/PR
- **API Contract**: `api-contract.yml` - Schemathesis property testing
- **API Smoke**: `api-smoke.yml` - Endpoint validation tests
- **Unit Tests**: `ci-unit.yml` - Comprehensive unit test suite
- **Security Scan**: `security-scan.yml` - Automated security scanning
- **Test Coverage**: `test-coverage.yml` - Coverage reporting to Codecov

### Deployment Process
```bash
# 1. Run database migrations on production
alembic upgrade head

# 2. Deploy using the production script
./deploy_prod_digest_pinned.ps1

# 3. Verify deployment
curl https://babyshield.cureviax.ai/healthz

# 4. Monitor logs
# Check AWS CloudWatch or application logs
```

## Common Pitfalls and Gotchas

### Import Masking
❌ **Don't** use broad try-except to hide import failures:
```python
# BAD - hides real import errors
try:
    from some_module import critical_function
except:
    pass
```

✅ **Do** let core imports fail fast:
```python
# GOOD - fails immediately if import is broken
from some_module import critical_function

# For optional features only
try:
    from optional_module import optional_function
except ImportError:
    optional_function = None
```

### Runtime Schema Modifications
❌ **Don't** modify database schema at runtime:
```python
# BAD - causes schema drift
def ensure_columns_exist(db):
    # Alter table at runtime
    db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS new_field")
```

✅ **Do** use Alembic migrations:
```bash
# GOOD - version-controlled schema changes
alembic revision --autogenerate -m "Add new_field to users"
alembic upgrade head
```

### Bare Except Clauses
❌ **Don't** use bare except clauses:
```python
# BAD - catches system exits and keyboard interrupts
try:
    risky_operation()
except:
    pass
```

✅ **Do** catch specific exceptions:
```python
# GOOD - only catches expected errors
try:
    risky_operation()
except (ValueError, KeyError) as e:
    logger.error(f"Operation failed: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

### Database Session Management
❌ **Don't** forget to close or commit sessions:
```python
# BAD - potential connection leaks
db = SessionLocal()
db.query(User).all()
# Session never closed
```

✅ **Do** use dependency injection or context managers:
```python
# GOOD - automatic cleanup
from fastapi import Depends

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
    # Session automatically closed by FastAPI
```

### Environment Variables
❌ **Don't** hardcode configuration:
```python
# BAD
DATABASE_URL = "postgresql://user:pass@localhost/db"
```

✅ **Do** use environment variables:
```python
# GOOD
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
```

## Git Workflow

### Branching Strategy
- `main` - Production-ready code (protected)
- `staging` - Integration branch for testing
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates
- `refactor/*` - Code refactoring

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat(auth): add JWT token refresh endpoint
fix(api): resolve 500 error on empty request body
docs(readme): update installation instructions
refactor(database): optimize query performance
test(api): add integration tests for user endpoints
chore(deps): update dependencies to latest versions
```

### Pull Request Checklist
Before creating a PR, ensure:
- [ ] All tests pass locally (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Linting passes (`ruff check .`)
- [ ] Coverage meets threshold (80%+)
- [ ] Documentation updated (if applicable)
- [ ] New tests added for new features
- [ ] Commit messages follow conventional commits
- [ ] No sensitive data in commits
- [ ] Database migrations created (if schema changes)

## Repository-Specific Notes

### Audit Findings (Resolved)
The repository underwent comprehensive Copilot audits in October 2025:
- ✅ Database files removed from git tracking
- ✅ Import masking issues resolved
- ✅ Runtime schema modifications replaced with Alembic migrations
- ✅ Redundant Dockerfiles removed
- ✅ Comprehensive `.gitignore` patterns added

See `COPILOT_AUDIT_COMPLETE.md` for full details.

### Key Files
- **Main API Entry**: `api/main_babyshield.py`
- **Database Config**: `core_infra/database.py`
- **Alembic Config**: `alembic.ini` and `alembic/`
- **Test Config**: `pytest.ini`
- **Requirements**: `config/requirements/requirements.txt`
- **Environment Example**: `.env.example`

### Periodic Maintenance
Run the comprehensive audit script periodically:
```powershell
.\scripts\comprehensive_audit.ps1
```

This checks for:
- Database files in git
- Duplicate files
- Backup/temp files
- Naming inconsistencies
- Large files
- Multiple Dockerfiles
- Python syntax errors

## Getting Help

- 📧 General: dev@babyshield.dev
- 🛡️ Security: security@babyshield.dev
- 💬 Discussions: [GitHub Discussions](https://github.com/BabyShield/babyshield-backend/discussions)
- 🐛 Issues: [GitHub Issues](https://github.com/BabyShield/babyshield-backend/issues)
- 📚 Documentation: See `CONTRIBUTING.md` for detailed contribution guidelines

## Quick Reference

### Useful Commands
```bash
# Development server
uvicorn api.main_babyshield:app --reload --port 8001

# Run tests
pytest
pytest -m unit
pytest -m integration
pytest --cov=. --cov-report=html

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1

# Code quality
black .
ruff check .
mypy .

# Audit check
.\scripts\comprehensive_audit.ps1
```

### Environment Variables (Required)
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP credentials JSON
- `FIREBASE_CREDENTIALS` - Firebase service account JSON

See `.env.example` for full list with descriptions.

---

**Last Updated**: October 6, 2025  
**Maintained By**: BabyShield Development Team
