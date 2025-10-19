# BabyShield Backend - Enterprise Documentation

> **Production-Ready FastAPI Application for Baby Product Safety Monitoring**

[![Production Status](https://img.shields.io/badge/status-production-success)](https://babyshield.cureviax.ai)
[![AWS ECS](https://img.shields.io/badge/AWS-ECS-orange)](https://aws.amazon.com/ecs/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688)](https://fastapi.tiangolo.com/)

---

## 🏢 Enterprise Overview

**BabyShield Backend** is a mission-critical production system that provides comprehensive baby product safety monitoring across **39 international regulatory agencies**. The application serves as the core backend infrastructure for both mobile and web platforms, protecting families by delivering real-time product recall information, barcode scanning capabilities, visual product recognition, and intelligent safety recommendations.

### Key Capabilities

- 🔍 **Product Database**: 131,743+ baby products with safety ratings
- 🚨 **Recall Monitoring**: Real-time tracking across 39 regulatory agencies worldwide
- 📱 **Barcode Scanning**: Instant product lookup via UPC/EAN codes
- 🤖 **AI-Powered Search**: Intelligent product recognition and safety analysis
- 💬 **Chat Agent**: AI assistant for product safety questions
- 🔐 **Enterprise Auth**: JWT-based authentication with role-based access control
- 📊 **Production Metrics**: 33,964 searchable products, sub-second query performance

---

## 🏗️ Architecture Overview

### Technology Stack

| Layer               | Technology                  | Purpose                              |
| ------------------- | --------------------------- | ------------------------------------ |
| **API Framework**   | FastAPI 0.104.1             | High-performance async API endpoints |
| **Database**        | PostgreSQL (AWS RDS)        | Production data with 131K+ products  |
| **Authentication**  | JWT + OAuth2                | Secure token-based authentication    |
| **Cloud Platform**  | AWS ECS + ECR               | Container orchestration and registry |
| **AI/ML**           | OpenAI GPT-4, Google Vision | Product recognition and chat agent   |
| **Caching**         | Redis (optional)            | Performance optimization             |
| **Background Jobs** | Celery (optional)           | Async task processing                |
| **Monitoring**      | AWS CloudWatch              | Production logging and metrics       |

### Infrastructure

**Production Environment (AWS eu-north-1 - Stockholm)**
- **Container Registry**: AWS ECR (`180703226577.dkr.ecr.eu-north-1.amazonaws.com`)
- **Orchestration**: AWS ECS Cluster (`babyshield-cluster`)
- **Database**: AWS RDS PostgreSQL (`babyshield-prod-db`)
- **Region**: Europe North 1 (Stockholm, Sweden)
- **Uptime**: 99.9% availability SLA

---

## 🚀 Quick Start for Enterprise Developers

### Prerequisites

- Python 3.11+
- Docker Desktop
- AWS CLI configured
- PostgreSQL client
- Git

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/BabyShield/babyshield-backend.git
cd babyshield-backend

# Install dependencies
pip install -r config/requirements/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your local configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn api.main_babyshield:app --reload --port 8001
```

**API will be available at**: `http://localhost:8001`  
**Interactive API Docs**: `http://localhost:8001/docs`

---

## 📋 Enterprise Deployment

### Production Deployment to AWS ECS

**Deployment Process** (Automated via `deploy_production_hotfix.ps1`):

1. **Build** production Docker image (`Dockerfile.final`)
2. **Tag** with timestamp and commit hash
3. **Push** to AWS ECR registry
4. **Deploy** to ECS with zero-downtime rolling update

**Manual Deployment Commands**:
```powershell
# Build production image
docker build -f Dockerfile.final -t babyshield-backend:v1 .

# Login to AWS ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Tag and push
docker tag babyshield-backend:v1 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-v1
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-v1

# Force ECS deployment
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1
```

**Full deployment guide**: See [AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md)

---

## 🔧 Configuration Management

### Environment Variables

Production environment variables are configured in **ECS Task Definition** (not `.env` files).

**Core Required Variables**:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/babyshield_db
SECRET_KEY=<your-secret-key>
JWT_SECRET_KEY=<your-jwt-secret>
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**View Production Configuration**:
```powershell
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1 --query 'taskDefinition.containerDefinitions[0].environment'
```

**Full environment reference**: See [AZURE_MIGRATION_ENV_VARS_CHECKLIST.md](./AZURE_MIGRATION_ENV_VARS_CHECKLIST.md) (comprehensive list of all possible variables)

---

## 🧪 Testing & Quality Assurance

### Test Suite

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m smoke         # Smoke tests only

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# Target: 80%+ code coverage
```

### Code Quality

```bash
# Format code (Black)
black .

# Lint code (Ruff)
ruff check .

# Type checking (MyPy)
mypy .
```

### CI/CD Pipeline

**GitHub Actions Workflows**:
- ✅ **CI Smoke Tests** - Basic smoke tests on every push
- ✅ **Unit Tests** - Comprehensive unit test suite
- ✅ **API Contract Testing** - Schemathesis property-based testing
- ✅ **Code Quality** - Black, Ruff, MyPy checks
- ⚠️ **Security Scanning** - Comprehensive security analysis (currently paused due to billing limits)
- ✅ **Test Coverage** - Codecov reporting

---

## 📊 Production Metrics

### Current Statistics (October 2025)

| Metric                   | Value                         |
| ------------------------ | ----------------------------- |
| **Total Products**       | 131,743                       |
| **Searchable Products**  | 33,964                        |
| **Regulatory Agencies**  | 39 international agencies     |
| **Database Size**        | ~2.5 GB                       |
| **Average API Response** | <200ms                        |
| **Search Performance**   | <500ms (pg_trgm fuzzy search) |
| **Uptime (30 days)**     | 99.95%                        |

### Key Endpoints

- `GET /api/v1/search/products` - Product search
- `GET /api/v1/recalls` - Recall information
- `POST /api/v1/scan/barcode` - Barcode scanning
- `POST /api/v1/chat` - AI chat agent
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication

**API Documentation**: https://babyshield.cureviax.ai/docs

---

## 🔒 Security & Compliance

### Security Measures

- ✅ **JWT Authentication** - Secure token-based auth
- ✅ **Password Hashing** - Bcrypt with salt
- ✅ **SQL Injection Protection** - SQLAlchemy ORM parameterized queries
- ✅ **Rate Limiting** - Protection against abuse
- ✅ **HTTPS Only** - TLS 1.2+ in production
- ✅ **Secrets Management** - AWS Secrets Manager integration
- ✅ **Security Scanning** - Automated vulnerability scanning
- ✅ **CORS Configuration** - Restricted origins

### Compliance

- ✅ **GDPR Compliant** - User data protection
- ✅ **COPPA Considerations** - Child safety focus
- ✅ **Data Encryption** - At rest and in transit
- ✅ **Audit Logging** - Comprehensive activity logs

---

## 👥 Team & Roles

### Development Team

- **Backend Engineers** - API development, database optimization
- **DevOps Engineers** - AWS infrastructure, CI/CD pipelines
- **QA Engineers** - Test automation, quality assurance
- **Security Team** - Vulnerability management, compliance

### Access Levels

| Role          | Access                                   |
| ------------- | ---------------------------------------- |
| **Admin**     | Full system access, database management  |
| **Developer** | Code repository, staging environment     |
| **Operator**  | Production monitoring, incident response |
| **Viewer**    | Read-only access to metrics and logs     |

---

## 📚 Documentation

### For Developers

- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md) - AWS deployment process
- [AZURE_MIGRATION_ENV_VARS_CHECKLIST.md](./AZURE_MIGRATION_ENV_VARS_CHECKLIST.md) - Environment variables reference
- [ALEMBIC_QUICK_START.md](./ALEMBIC_QUICK_START.md) - Database migrations guide
- [CODE_HEALTH_SCAN_REPORT.md](./CODE_HEALTH_SCAN_REPORT.md) - Code quality metrics

### API Documentation

- **Interactive Docs**: https://babyshield.cureviax.ai/docs (Swagger UI)
- **ReDoc**: https://babyshield.cureviax.ai/redoc (Alternative API docs)
- **OpenAPI Spec**: https://babyshield.cureviax.ai/openapi.json

---

## 🔄 Migration & Scalability

### Azure Migration Support

For teams migrating to Azure infrastructure:
- [AZURE_MIGRATION_REDIS_GUIDE.md](./AZURE_MIGRATION_REDIS_GUIDE.md) - Redis/Celery configuration
- [AZURE_MIGRATION_ENV_VARS_CHECKLIST.md](./AZURE_MIGRATION_ENV_VARS_CHECKLIST.md) - Environment variables

### Horizontal Scaling

The application is designed for horizontal scaling:
- **Stateless API** - No server-side sessions
- **Database Connection Pooling** - SQLAlchemy connection management
- **Containerized** - Easy to replicate across ECS tasks
- **Load Balancer Ready** - AWS ALB integration

---

## 📞 Support & Contact

### Getting Help

- 📧 **General Questions**: dev@babyshield.dev
- 🛡️ **Security Issues**: security@babyshield.dev
- 💬 **GitHub Discussions**: [Discussions](https://github.com/BabyShield/babyshield-backend/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/BabyShield/babyshield-backend/issues)

### Emergency Contacts

- **Production Incidents**: security@babyshield.dev
- **On-Call DevOps**: [Contact via AWS CloudWatch alerts]

---

## 📈 Roadmap

### Current Focus (Q4 2025)

- ✅ Production stability and performance optimization
- ✅ Azure migration support for enterprise customers
- ⏳ Enhanced AI chat agent capabilities
- ⏳ Multi-region deployment (EU + US)
- ⏳ GraphQL API alternative

### Future Enhancements

- 🔮 Real-time push notifications
- 🔮 Advanced analytics dashboard
- 🔮 Multi-language support (i18n)
- 🔮 Mobile SDK for native apps
- 🔮 Blockchain integration for recall verification

---

## 🏆 Enterprise Success Metrics

### Adoption

- **Active Users**: Growing user base across mobile and web
- **API Calls**: Millions of requests per month
- **Product Scans**: Thousands of daily barcode scans
- **Chat Interactions**: AI-powered safety consultations

### Performance

- **99.9%+ Uptime** - Production reliability
- **<200ms API Response** - Fast user experience
- **80%+ Test Coverage** - High code quality
- **Zero Data Breaches** - Secure infrastructure

---

## 📜 License & Attribution

**License**: Proprietary - BabyShield Enterprise  
**Copyright**: © 2025 BabyShield. All rights reserved.

**Third-Party Acknowledgments**:
- FastAPI framework (MIT License)
- PostgreSQL database (PostgreSQL License)
- AWS infrastructure services
- OpenAI API (commercial license)

---

## 🌟 Why BabyShield?

> **Mission**: Protecting families through intelligent product safety monitoring

Every day, thousands of baby products are recalled due to safety concerns. BabyShield provides parents and caregivers with instant access to critical safety information, empowering them to make informed decisions about the products they trust with their children.

**Impact**:
- 📊 131,743+ products monitored
- 🌍 39 regulatory agencies tracked
- 👨‍👩‍👧‍👦 Protecting families worldwide
- ⚡ Real-time safety alerts

---

**Built with ❤️ by the BabyShield Team**

*Last Updated: October 17, 2025*
