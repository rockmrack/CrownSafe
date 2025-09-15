"""
Critical Production Fixes - Must implement before AWS deployment
These are the absolute minimum requirements for handling 1000+ users
"""

# ============================================================
# 1. RATE LIMITING (Prevents API abuse)
# ============================================================

RATE_LIMITING_CODE = '''
# Add to api/main_babyshield.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute", "1000 per hour"],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/1")
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add to specific endpoints
@app.get("/api/v1/safety/check")
@limiter.limit("50 per minute")  # Stricter limit for expensive operations
async def safety_check(request: Request):
    pass
'''

# ============================================================
# 2. HEALTH CHECK ENDPOINTS (For AWS Load Balancer)
# ============================================================

HEALTH_CHECK_CODE = '''
# Add to api/main_babyshield.py

@app.get("/health")
async def health_check():
    """Health check for load balancer"""
    try:
        # Check database
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Check Redis
        r = redis.Redis(host=REDIS_HOST, port=6379, db=0)
        r.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "babyshield-api",
            "version": "2.4.0"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.get("/ready")
async def readiness_check():
    """Readiness check for container orchestration"""
    return {"ready": True}
'''

# ============================================================
# 3. JWT AUTHENTICATION (Security)
# ============================================================

JWT_AUTH_CODE = '''
# Add to core_infra/auth.py

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return user_id

# Use in endpoints:
@app.get("/api/v1/protected")
async def protected_route(current_user: str = Depends(get_current_user)):
    return {"user": current_user}
'''

# ============================================================
# 4. DATABASE CONNECTION POOLING (Scale)
# ============================================================

DATABASE_POOL_CODE = '''
# Update core_infra/database.py

from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "50")),
    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "100")),
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Never log queries in production
)
'''

# ============================================================
# 5. CIRCUIT BREAKER (Resilience)
# ============================================================

CIRCUIT_BREAKER_CODE = '''
# Add to core_infra/circuit_breaker.py

from pybreaker import CircuitBreaker
import redis

# Circuit breaker for external APIs
external_api_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    exclude=[KeyError, ValueError]
)

# Circuit breaker for database
db_breaker = CircuitBreaker(
    fail_max=10,
    reset_timeout=30
)

# Use with decorators:
@external_api_breaker
def call_external_api():
    # API call that might fail
    pass

@db_breaker
def database_operation():
    # Database operation
    pass
'''

# ============================================================
# 6. REQUEST ID TRACKING (Debugging)
# ============================================================

REQUEST_ID_CODE = '''
# Add middleware to api/main_babyshield.py

import uuid
from fastapi import Request

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    logger.info(f"Request {request.method} {request.url.path}", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path
    })
    
    return response
'''

# ============================================================
# 7. ASYNC S3 UPLOADS (File handling)
# ============================================================

S3_UPLOAD_CODE = '''
# Add to core_infra/s3_handler.py

import aioboto3
from typing import BinaryIO

class S3Handler:
    def __init__(self):
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.region = os.getenv("AWS_REGION", "us-east-1")
    
    async def upload_file(self, file_obj: BinaryIO, key: str):
        """Upload file to S3 asynchronously"""
        async with aioboto3.Session().client("s3", region_name=self.region) as s3:
            await s3.upload_fileobj(file_obj, self.bucket_name, key)
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
    
    async def generate_presigned_url(self, key: str, expiration: int = 3600):
        """Generate presigned URL for secure access"""
        async with aioboto3.Session().client("s3", region_name=self.region) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration
            )
            return url
'''

# ============================================================
# 8. METRICS COLLECTION (Monitoring)
# ============================================================

METRICS_CODE = '''
# Add to core_infra/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
request_count = Counter("app_requests_total", "Total requests", ["method", "endpoint", "status"])
request_duration = Histogram("app_request_duration_seconds", "Request duration", ["method", "endpoint"])
active_connections = Gauge("app_active_connections", "Active connections")
error_count = Counter("app_errors_total", "Total errors", ["type"])

# Use in middleware
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()
    
    active_connections.inc()
    
    try:
        response = await call_next(request)
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        return response
    except Exception as e:
        error_count.labels(type=type(e).__name__).inc()
        raise
    finally:
        active_connections.dec()
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(time.time() - start_time)
'''

# ============================================================
# CRITICAL DEPENDENCIES TO INSTALL
# ============================================================

DEPENDENCIES = """
# Add to requirements.txt

# Production essentials
gunicorn==21.2.0
uvloop==0.19.0
httptools==0.6.1

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
slowapi==0.1.9

# AWS
boto3==1.34.0
aioboto3==12.0.0

# Monitoring
prometheus-client==0.19.0
sentry-sdk==1.39.0
datadog==0.47.0

# Resilience
pybreaker==1.0.1
tenacity==8.2.3

# Performance
orjson==3.9.10
ujson==5.9.0
"""

print("✅ Critical production fixes documented!")
print("\nThese components are ESSENTIAL for production:")
print("  1. Rate Limiting - Prevents API abuse")
print("  2. Health Checks - Required for AWS load balancer")
print("  3. JWT Authentication - Secures your API")
print("  4. Connection Pooling - Handles concurrent users")
print("  5. Circuit Breakers - Prevents cascade failures")
print("  6. Request Tracking - Essential for debugging")
print("  7. S3 Uploads - Scalable file storage")
print("  8. Metrics - Monitor system health")
print("\n⚠️ Implement ALL of these before going to production!")
