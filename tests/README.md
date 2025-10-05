# BabyShield Backend Test Suite

## 📁 Test Structure

```
tests/
├── unit/               # Unit tests (fast, isolated)
│   ├── test_auth_service.py
│   ├── test_barcode_service.py
│   └── test_validators.py
├── integration/        # Integration tests (database, external services)
│   └── test_api_integration.py
├── security/           # Security-focused tests
│   └── test_security_headers.py
├── performance/        # Performance benchmarks
│   └── test_performance.py
└── conftest.py        # Shared pytest fixtures
```

## 🧪 Running Tests

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

### Run Specific Test File
```bash
pytest tests/unit/test_auth_service.py -v
```

### Run Tests Matching Pattern
```bash
pytest -k "test_login" -v
```

## 📊 Coverage Reports

### Generate HTML Coverage Report
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Generate XML for CI/CD
```bash
pytest --cov=. --cov-report=xml
```

## 🏷️ Test Markers

Tests are marked with categories:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests requiring database/services
- `@pytest.mark.security` - Security-focused tests
- `@pytest.mark.performance` - Performance benchmarks
- `@pytest.mark.smoke` - Critical path smoke tests
- `@pytest.mark.skip` - Temporarily skipped tests

Run tests by marker:
```bash
pytest -m unit
pytest -m "not integration"  # Skip integration tests
```

## 🔧 Configuration

### pytest.ini
Configuration is in `pytest.ini` at the project root.

### Coverage Settings
- Minimum coverage: 80% (configured in pytest.ini)
- Coverage reports uploaded to Codecov in CI/CD
- Branch coverage enabled

## 📝 Writing Tests

### Unit Test Example
```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
class TestAuthService:
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        from core_infra.auth import hash_password, verify_password
        
        password = "SecurePass123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
```

### Integration Test Example
```python
@pytest.mark.integration
async def test_api_endpoint(app_client):
    """Test full API endpoint with database"""
    response = await app_client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "Test123!"}
    )
    assert response.status_code == 201
```

## 🚀 CI/CD Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Can be triggered manually via GitHub Actions

### GitHub Actions Workflows
- `.github/workflows/test-coverage.yml` - Main test suite with coverage
- `.github/workflows/api-contract.yml` - API contract testing with Schemathesis
- `.github/workflows/security-scan.yml` - Security scanning

## 📈 Coverage Goals

- **Overall**: 80% minimum
- **New code**: 85% minimum
- **Critical paths**: 95% minimum

## 🛠️ Troubleshooting

### Import Errors
Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### Database Tests Failing
Check test database is running:
```bash
docker-compose up -d postgres-test
```

### Slow Tests
Use pytest-xdist for parallel execution:
```bash
pytest -n auto
```

## 📚 Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.io/)
