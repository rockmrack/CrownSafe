[![API Smoke — Endpoints CSV](https://github.com/rockmrack/CrownSafe/actions/workflows/api-smoke.yml/badge.svg?branch=main)](https://github.com/rockmrack/CrownSafe/actions/workflows/api-smoke.yml)

# CrownSafe Backend

[![Test Coverage](https://github.com/rockmrack/CrownSafe/actions/workflows/test-coverage.yml/badge.svg)](https://github.com/rockmrack/CrownSafe/actions/workflows/test-coverage.yml)
[![codecov](https://codecov.io/gh/rockmrack/CrownSafe/branch/main/graph/badge.svg)](https://codecov.io/gh/rockmrack/CrownSafe)
[![API Contract](https://github.com/rockmrack/CrownSafe/actions/workflows/api-contract.yml/badge.svg)](https://github.com/rockmrack/CrownSafe/actions/workflows/api-contract.yml)
[![Security Scan](https://github.com/rockmrack/CrownSafe/actions/workflows/security-scan.yml/badge.svg)](https://github.com/rockmrack/CrownSafe/actions/workflows/security-scan.yml)

Production-ready backend for the CrownSafe agent platform, providing comprehensive product safety monitoring across 39 international regulatory agencies.

## 🧪 Testing & Quality Assurance

- **Unit Tests**: Comprehensive unit test suite with pytest
- **Coverage**: 80%+ code coverage with coverage.py and Codecov integration  
- **API Testing**: Contract testing with Schemathesis (Hypothesis-based property testing)
- **Security**: Automated security scanning with multiple tools
- **Performance**: Benchmark tests for critical paths
- **CI/CD**: Automated testing on every PR and push to main

See [tests/README.md](tests/README.md) for detailed testing documentation.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose
- AWS Account (for ECR, S3)
- Google Cloud Account (for Vision API)

### Installation

```bash
# Clone the repository
git clone https://github.com/rockmrack/CrownSafe.git
cd CrownSafe

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r config/requirements/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn api.main_babyshield:app --reload --port 8001
```

### Docker Deployment

```bash
# Build production image
docker build -f Dockerfile.final -t crownsafe-backend:latest .

# Run with Docker Compose
docker-compose up -d
```

## 🏗️ Architecture

```
CrownSafe/
├── api/                    # FastAPI endpoints
│   ├── main_babyshield.py # Main application entry
│   ├── auth_endpoints.py  # Authentication & authorization
│   ├── barcode_endpoints.py
│   ├── recalls_endpoints.py
│   └── ...
├── agents/                 # Intelligent agents
│   ├── planning/          # Task planning agents
│   ├── routing/           # Request routing
│   ├── visual/            # Image recognition
│   └── ...
├── core_infra/            # Core infrastructure
│   ├── database.py        # Database connections
│   ├── logging_setup.py   # Logging configuration
│   └── ...
├── tests/                 # 500+ comprehensive tests
│   ├── test_suite_1_*.py # Import & config tests
│   ├── test_suite_2_*.py # API endpoint tests
│   ├── test_suite_3_*.py # Database tests
│   ├── test_suite_4_*.py # Security tests
│   └── test_suite_5_*.py # Integration tests
├── workers/               # Background task workers
├── alembic/               # Database migrations
└── docs/                  # Documentation
```

## 🔌 API Endpoints

### Health & Monitoring
- `GET /healthz` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /api/v1/monitoring/status` - System status

### Product Recalls
- `GET /api/v1/recalls` - List recalls with pagination
- `GET /api/v1/recalls/{id}` - Get recall details
- `POST /api/v1/recalls/search` - Search recalls

### Barcode Scanning
- `POST /api/v1/barcode/scan` - Scan barcode
- `GET /api/v1/barcode/lookup?code={code}` - Lookup product

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/password-reset/request` - Reset password

### Notifications
- `GET /api/v1/notifications` - List notifications
- `POST /api/v1/notifications/{id}/read` - Mark as read

Full API documentation: https://crownsafe.cureviax.ai/docs

## 🧪 Testing

We maintain **500+ comprehensive tests** covering:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test suites
pytest tests/test_suite_1_imports_and_config.py -v
pytest tests/test_suite_2_api_endpoints.py -v
pytest tests/test_suite_3_database_models.py -v
pytest tests/test_suite_4_security_validation.py -v
pytest tests/test_suite_5_integration_performance.py -v

# Run API contract tests
pytest tests/test_api_contract.py -v

# Run security tests only
pytest -m security tests/
```

### Test Coverage
- **Total Tests**: 500
- **Pass Rate**: 88.6% (443 passed, 57 skipped)
- **Coverage**: 80%+ on critical paths
- **Security**: SQL injection, XSS, CSRF, authentication tests
- **Performance**: Response time, memory, load tests

See [FINAL_TEST_RESULTS_500.md](FINAL_TEST_RESULTS_500.md) for detailed test report.

## 🔒 Security

### Best Practices
- ✅ JWT-based authentication with bcrypt password hashing
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS prevention (proper encoding)
- ✅ CSRF protection tokens
- ✅ Rate limiting on sensitive endpoints
- ✅ Secrets management (AWS Secrets Manager)
- ✅ HTTPS only in production
- ✅ Regular security scanning (Bandit, Safety)

### Reporting Security Issues
Please report security vulnerabilities to **security@crownsafe.com**  
See [SECURITY.md](SECURITY.md) for our security policy.

## 🚀 Deployment

### Production Environment
- **URL**: https://crownsafe.cureviax.ai
- **Container Registry**: AWS ECR
- **Infrastructure**: AWS ECS/EKS
- **Database**: AWS RDS PostgreSQL
- **Monitoring**: CloudWatch + Prometheus + Grafana

### Latest Deployment
- **Image**: `production-20251009-1544-tests`
- **Digest**: `sha256:a4d0012c8179f7dd8f8df3dbcd30f34574c06c39938c86bfa148b99335575173`
- **Status**: ✅ Healthy

### Deployment Process
```bash
# Build production image
./scripts/build_production.sh

# Push to ECR
./scripts/push_to_ecr.sh

# Deploy to staging
./scripts/deploy_staging.sh

# Deploy to production (requires approval)
./scripts/deploy_production.sh
```

## 📊 Monitoring & Observability

### Metrics
- Request rate, latency, error rate
- Database query performance
- Cache hit rates
- Memory and CPU usage
- Background worker queue depth

### Logging
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Integration with CloudWatch Logs
- Request ID tracing

### Alerts
- High error rate (>5%)
- Slow response times (>2s)
- Database connection failures
- High memory usage (>80%)
- Failed background jobs

## 🛠️ Development

### Code Quality Tools
```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .

# Security scanning
bandit -r api/ core_infra/ agents/ workers/

# Dependency vulnerability scanning
safety check
```

### Git Workflow
1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit: `git commit -m "feat: your feature"`
3. Push branch: `git push origin feature/your-feature`
4. Create Pull Request
5. Wait for CI/CD checks to pass
6. Request code review
7. Merge after approval

### Commit Message Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Coding standards
- Pull request process
- Testing requirements

## 📚 Documentation

- **API Documentation**: https://crownsafe.cureviax.ai/docs (Swagger/OpenAPI)
- **Test Results**: [FINAL_TEST_RESULTS_500.md](FINAL_TEST_RESULTS_500.md)
- **Deployment Guide**: [DEPLOYMENT_OCTOBER_9_BUGFIXES.md](DEPLOYMENT_OCTOBER_9_BUGFIXES.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Copilot Instructions**: [.github/copilot-instructions.md](.github/copilot-instructions.md)

## 🌐 Related Projects

- **CrownSafe Mobile App**: iOS and Android applications
- **CrownSafe Web**: React-based web application
- **CrownSafe Admin**: Administrative dashboard

## 📈 Project Status

- **Version**: 1.0.0
- **Status**: Production
- **Last Updated**: October 26, 2025
- **Maintained**: ✅ Actively maintained
- **Issues**: [GitHub Issues](https://github.com/rockmrack/CrownSafe/issues)
- **Pull Requests**: [GitHub PRs](https://github.com/rockmrack/CrownSafe/pulls)

## 📞 Support

- **Technical Support**: dev@crownsafe.com
- **Security Issues**: security@crownsafe.com
- **General Inquiries**: info@crownsafe.com
- **Discussions**: [GitHub Discussions](https://github.com/rockmrack/CrownSafe/discussions)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI framework for excellent async API support
- SQLAlchemy for robust database ORM
- Schemathesis for comprehensive API testing
- All contributors and supporters of the CrownSafe project

---

**Made with ❤️ by the CrownSafe Team**

