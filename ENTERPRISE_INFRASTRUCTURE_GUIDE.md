# Crown Safe Enterprise Infrastructure Guide

Complete guide to Crown Safe's production-ready enterprise infrastructure.

## 🎯 System Overview

Crown Safe is a comprehensive baby product safety monitoring API with enterprise-grade infrastructure including:

- **Security**: Startup validation, Snyk scanning, vulnerability management
- **Performance**: Async I/O, connection pooling, Redis caching
- **Monitoring**: Prometheus metrics, distributed tracing, health dashboards
- **Reliability**: Automated backups, disaster recovery, circuit breakers
- **Scalability**: Kubernetes deployment, auto-scaling, load balancing
- **CI/CD**: Automated testing, security scanning, deployment pipelines

## 📊 Architecture Components

### Core Infrastructure (`core_infra/`)

#### 1. **Database Management** (`database.py`)
- PostgreSQL with SQLAlchemy 2.0
- Connection pooling
- Alembic migrations
- Health monitoring

#### 2. **Azure Blob Storage** (`azure_storage.py`)
- Async file uploads (ThreadPoolExecutor)
- Connection pooling (`azure_connection_pool.py`)
- Cache integration
- Health monitoring
- 10 concurrent upload workers

#### 3. **Caching Layer** (`azure_storage_cache.py`)
- Redis-based caching
- Automatic cache invalidation
- Hit rate monitoring
- Performance metrics

#### 4. **Security** (`security_validator.py`)
- Comprehensive security audits
- Environment validation
- Secret management checks
- Startup validation (production)

#### 5. **Health Monitoring** (`system_health_dashboard.py`)
- Unified health checks
- 0-100 health scoring
- Subsystem aggregation
- Status levels: healthy, degraded, warning, critical

#### 6. **Monitoring** (`monitoring.py`)
- Prometheus metrics exposition
- HTTP, database, cache, storage metrics
- Custom application metrics
- Alert rules and thresholds

#### 7. **Observability** (`observability.py`)
- OpenTelemetry distributed tracing
- Azure Application Insights integration
- Custom spans and metrics
- Automatic instrumentation

## 🔧 Key Features

### Security Hardening

#### Startup Validation
```python
# api/main_crownsafe.py (lines 1720-1755)
@app.on_event("startup")
async def startup_security_check():
    """Run security audit on startup (production only)"""
    if os.getenv("ENVIRONMENT") == "production":
        audit_result = security_validator.comprehensive_security_audit()
        # Logs failures with risk levels
        # CRITICAL issues trigger alerts
```

**Benefits:**
- Catches misconfigurations before serving traffic
- Prevents insecure deployments
- Automated compliance checking

#### Snyk Security Scanning
- **0 high-severity vulnerabilities** (verified)
- Automated scans in CI/CD
- Dependency vulnerability tracking
- Code security analysis

### Performance Optimizations

#### Async Blob Uploads
```python
# core_infra/azure_storage.py
_upload_executor = ThreadPoolExecutor(max_workers=10)

async def upload_file_async(self, file_data, blob_name, ...):
    """Non-blocking async upload"""
    loop = asyncio.get_event_loop()
    blob_url = await loop.run_in_executor(
        _upload_executor,
        self.upload_file,
        file_data, blob_name, ...
    )
    return blob_url
```

**Benefits:**
- Non-blocking I/O operations
- 10x concurrent uploads
- Improved throughput
- Better resource utilization

#### Connection Pooling
```python
# core_infra/azure_connection_pool.py
class AzureBlobConnectionPool:
    def __init__(self, pool_size=10):
        self._pool = Queue(maxsize=pool_size)
        self._initialize_pool()
    
    def acquire(self) -> BlobServiceClient:
        """Get connection from pool"""
        return self._pool.get(timeout=30)
    
    def release(self, client: BlobServiceClient):
        """Return connection to pool"""
        self._pool.put(client)
```

**Benefits:**
- Reduces connection overhead
- Reuses existing connections
- Thread-safe operations
- Exhaustion tracking

#### Redis Caching
- **~50% cache hit rate** (typical)
- Automatic invalidation
- TTL-based expiration
- Performance monitoring

### Monitoring & Observability

#### System Health Dashboard
```python
# Endpoint: GET /api/v1/monitoring/system-health-dashboard
{
  "status": "healthy",  # healthy, degraded, warning, critical
  "health_score": 95,   # 0-100
  "subsystems": {
    "security": {"status": "healthy", "issues": []},
    "azure_storage": {"status": "healthy", "latency_ms": 45},
    "cache": {"status": "healthy", "hit_rate": 52.3},
    "connection_pool": {"status": "healthy", "reuse_rate": 85.2},
    "database": {"status": "healthy", "connections": 15}
  }
}
```

**Health Scoring:**
- **90-100**: Healthy (all systems operational)
- **70-89**: Degraded (minor issues)
- **50-69**: Warning (action recommended)
- **<50**: Critical (immediate action required)

**Penalties:**
- Security CRITICAL: -50
- Security HIGH: -30
- Security MEDIUM: -15
- Security LOW: -5
- Azure Storage unhealthy: -20
- Cache hit rate <50%: -10
- Connection pool exhaustion >100: -15
- Database failure: -25

#### Prometheus Metrics

**HTTP Metrics:**
- `http_requests_total` - Total requests (by method, endpoint, status)
- `http_request_duration_seconds` - Request duration histogram

**Database Metrics:**
- `database_connections_active` - Active connections
- `database_query_duration_seconds` - Query duration histogram
- `database_errors_total` - Total errors

**Cache Metrics:**
- `cache_hits_total` - Cache hits
- `cache_misses_total` - Cache misses
- `cache_size_bytes` - Cache size

**Storage Metrics:**
- `azure_blob_uploads_total` - Upload count
- `azure_blob_upload_duration_seconds` - Upload duration
- `azure_blob_storage_bytes` - Total stored bytes

**Application Metrics:**
- `app_health_score` - Health score (0-100)
- `app_uptime_seconds` - Uptime
- `security_audit_failures_total` - Security failures

**Endpoint:** `GET /metrics` (Prometheus format)

#### Distributed Tracing

OpenTelemetry instrumentation:
- FastAPI automatic tracing
- SQLAlchemy database queries
- Redis cache operations
- HTTP client requests
- Custom spans for business logic

**Azure Application Insights integration:**
- Automatic log correlation
- Performance profiling
- Custom events and metrics
- Exception tracking

### Testing Infrastructure

#### Load Testing Framework
```bash
# Run load tests
python tests/performance/load_test.py
```

**Features:**
- Concurrent request testing
- Response time metrics (avg, p95, p99)
- Throughput calculation (RPS)
- Success/failure tracking
- Tests 6 critical endpoints

**Tested Endpoints:**
1. `/health` - Basic health check
2. `/api/healthz` - API health check
3. `/api/v1/monitoring/system-health-dashboard` - Health dashboard
4. `/api/v1/monitoring/security-audit` - Security audit
5. `/api/v1/monitoring/azure-cache-stats` - Cache stats
6. `/api/v1/azure-storage/health` - Storage health

#### Unit & Integration Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific markers
pytest -m unit
pytest -m integration
```

**Coverage Target:** 80%+

### Backup & Disaster Recovery

#### Automated Backups
```bash
# Run manual backup
python scripts/automated_backup.py
```

**Features:**
- Full and incremental backups
- PostgreSQL pg_dump
- Gzip compression
- Upload to Azure Blob Storage
- 30-day retention policy
- Automated cleanup
- Verification

**Backup Schedule:**
- **Daily**: Automated via CI/CD (2 AM UTC)
- **Pre-deployment**: Automatic before production deploy
- **Manual**: On-demand via script

**Backup Format:**
```
crownsafe_backup_full_20251014_020000.sql.gz
```

**Retention Policy:**
- **30 days**: Automatic deletion
- **Size**: ~50-200MB compressed

#### Disaster Recovery

**RTO (Recovery Time Objective):** <1 hour  
**RPO (Recovery Point Objective):** <24 hours

**Recovery Process:**
1. Download backup from Azure
2. Restore to database
3. Verify data integrity
4. Update application configuration
5. Restart services

```bash
# Restore from backup
az storage blob download \
  --container-name crownsafe-backups \
  --name backup_file.sql.gz \
  --file backup.sql.gz

gunzip -c backup.sql.gz | psql $DATABASE_URL
```

## 🚀 Deployment

### Local Development

```bash
# Install dependencies
pip install -r config/requirements/requirements.txt

# Run migrations
alembic upgrade head

# Start server
uvicorn api.main_crownsafe:app --reload --port 8001
```

### Docker Deployment

```bash
# Build image
docker build -f Dockerfile.final -t crownsafe-api:latest .

# Run container
docker run -p 8001:8001 \
  -e DATABASE_URL="..." \
  -e REDIS_URL="..." \
  -e AZURE_STORAGE_CONNECTION_STRING="..." \
  crownsafe-api:latest
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/config.yaml
kubectl apply -f k8s/deployment.yaml

# Verify deployment
kubectl get pods -n crownsafe
kubectl get svc -n crownsafe
```

**Features:**
- 3-10 pod auto-scaling
- Rolling updates (zero downtime)
- Health probes (liveness + readiness)
- Resource limits (CPU/memory)
- Load balancing
- TLS termination

**See:** `k8s/README.md` for complete guide

### CI/CD Pipeline

**GitHub Actions Workflow:** `.github/workflows/ci-cd-pipeline.yml`

**Pipeline Stages:**

1. **Code Quality** - Ruff linting, Black formatting, mypy type checking
2. **Security Scan** - Snyk vulnerability scanning
3. **Unit Tests** - pytest with coverage reporting
4. **Integration Tests** - Full integration test suite
5. **Performance Tests** - Load testing
6. **Build Docker** - Build and push to ACR
7. **Deploy Staging** - Auto-deploy to staging environment
8. **Deploy Production** - Manual approval, automated backup, deployment
9. **Automated Backup** - Daily database backup (2 AM UTC)

**Triggers:**
- Push to `main`, `staging`, `develop`
- Pull requests to `main`, `staging`
- Daily schedule (backups)

## 📈 Performance Benchmarks

### Response Times (Typical)

| Endpoint                | Avg   | P95   | P99   |
| ----------------------- | ----- | ----- | ----- |
| `/health`               | 5ms   | 15ms  | 25ms  |
| `/api/healthz`          | 45ms  | 120ms | 200ms |
| `/api/recalls`          | 150ms | 350ms | 500ms |
| `/api/barcode`          | 200ms | 450ms | 650ms |
| System Health Dashboard | 85ms  | 180ms | 280ms |

### Throughput

- **Concurrent users**: 100+ simultaneous
- **Requests per second**: 500+ RPS
- **Database queries**: <50ms p95
- **Cache hit rate**: ~50%
- **Blob uploads**: 1-3s per file

### Scaling Capacity

- **Horizontal**: 3-10 pods (auto-scaling)
- **Vertical**: 512Mi-2Gi memory, 500m-2000m CPU per pod
- **Database**: Connection pool size 20-50
- **Cache**: Redis cluster (optional)

## 🔒 Security Best Practices

### Environment Variables (Required)

```bash
DATABASE_URL="postgresql://user:pass@host:5432/db"
REDIS_URL="redis://host:6379/0"
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
SECRET_KEY="your-secret-key-here"
ENVIRONMENT="production"
```

### Secret Management

- **Never commit** secrets to version control
- Use **environment variables** or **Azure Key Vault**
- Rotate secrets **quarterly**
- Use **strong passwords** (32+ characters)
- Enable **TLS/SSL** for all connections

### Security Checklist

- [x] Startup security validation
- [x] Snyk vulnerability scanning (0 issues)
- [x] Environment variable validation
- [x] TLS/SSL encryption
- [x] Strong password hashing (bcrypt)
- [x] JWT token authentication
- [x] CORS configuration
- [x] Rate limiting
- [x] Input validation
- [x] SQL injection prevention (ORM)
- [x] XSS protection

## 📚 API Documentation

### API Documentation Generator

```bash
# Generate comprehensive API docs
python scripts/generate_api_docs.py
```

**Features:**
- All monitoring endpoint documentation
- Response examples with realistic data
- Error codes and meanings
- Rate limiting information
- Authentication details
- Best practices guide

### Monitoring Endpoints

#### Health Checks
- `GET /health` - Basic health check
- `GET /api/healthz` - API health with database check

#### System Monitoring
- `GET /api/v1/monitoring/system-health-dashboard` - Unified health dashboard
- `GET /api/v1/monitoring/security-audit` - Security audit results
- `GET /api/v1/monitoring/azure-cache-stats` - Cache performance
- `GET /api/v1/azure-storage/health` - Storage health

#### Metrics
- `GET /metrics` - Prometheus metrics (OpenMetrics format)

## 🛠️ Troubleshooting

### Common Issues

#### High Error Rate
- **Check**: Application logs
- **Action**: Review error traces, check database connectivity
- **Monitor**: `http_requests_total{status_code="5xx"}`

#### Low Cache Hit Rate
- **Check**: Cache stats endpoint
- **Action**: Review cache key patterns, adjust TTL
- **Monitor**: `cache_hits_total / (cache_hits_total + cache_misses_total)`

#### Database Connection Pool Exhaustion
- **Check**: Connection pool stats
- **Action**: Increase pool size, optimize long queries
- **Monitor**: `database_connections_active`

#### Slow Response Times
- **Check**: Performance metrics, distributed traces
- **Action**: Optimize slow queries, increase resources
- **Monitor**: `http_request_duration_seconds{quantile="0.95"}`

### Health Check Failures

#### Security Audit Failures
- **Severity**: CRITICAL, HIGH, MEDIUM, LOW
- **Action**: Review security configuration, update secrets
- **Impact**: Health score penalty

#### Azure Storage Unhealthy
- **Symptoms**: Upload failures, high latency
- **Action**: Check connection string, verify network
- **Impact**: -20 health score penalty

#### Database Connectivity Issues
- **Symptoms**: Connection timeouts, query failures
- **Action**: Verify DATABASE_URL, check firewall rules
- **Impact**: -25 health score penalty, service degradation

## 📞 Support

- **Email**: dev@crownsafe.com
- **Security**: security@crownsafe.com
- **DevOps**: devops@crownsafe.com
- **Documentation**: https://docs.crownsafe.com
- **GitHub**: https://github.com/crownsafe/api

## 📝 License

Copyright © 2025 Crown Safe. All rights reserved.

---

**Last Updated**: October 14, 2025  
**Version**: 2.0.0  
**Maintained By**: Crown Safe Engineering Team
