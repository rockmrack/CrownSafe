"""
Task 14: Monitoring, Metrics, and SLO Implementation
Provides Prometheus metrics, health checks, and monitoring endpoints
"""

from fastapi import APIRouter, Response, Request, Depends, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    push_to_gateway,
)
from prometheus_client.core import CollectorRegistry
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time
import asyncio
import logging
import psutil
import os
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
import json

logger = logging.getLogger(__name__)

# Create custom registry to avoid conflicts
REGISTRY = CollectorRegistry()

# ========================= METRICS DEFINITIONS =========================

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
    registry=REGISTRY,
)

http_request_size_bytes = Summary(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    registry=REGISTRY,
)

http_response_size_bytes = Summary(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    registry=REGISTRY,
)

# Error metrics
error_total = Counter(
    "error_total", "Total number of errors", ["type", "endpoint"], registry=REGISTRY
)

# Rate limiting metrics
rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total number of rate limit hits",
    ["endpoint", "user"],
    registry=REGISTRY,
)

rate_limit_remaining = Gauge(
    "rate_limit_remaining",
    "Remaining rate limit for user",
    ["endpoint", "user"],
    registry=REGISTRY,
)

# Business metrics
barcode_scans_total = Counter(
    "barcode_scans_total",
    "Total number of barcode scans",
    ["type", "result"],
    registry=REGISTRY,
)

search_queries_total = Counter(
    "search_queries_total",
    "Total number of search queries",
    ["type"],
    registry=REGISTRY,
)

recalls_found_total = Counter(
    "recalls_found_total",
    "Total number of recalls found",
    ["severity"],
    registry=REGISTRY,
)

# System metrics
system_memory_usage = Gauge(
    "system_memory_usage_bytes", "System memory usage in bytes", registry=REGISTRY
)

system_cpu_usage = Gauge(
    "system_cpu_usage_percent", "System CPU usage percentage", registry=REGISTRY
)

database_connections_active = Gauge(
    "database_connections_active",
    "Number of active database connections",
    registry=REGISTRY,
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    registry=REGISTRY,
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total", "Total number of cache hits", ["cache_type"], registry=REGISTRY
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
    ["cache_type"],
    registry=REGISTRY,
)

cache_size = Gauge(
    "cache_size_items", "Number of items in cache", ["cache_type"], registry=REGISTRY
)

# Application info
app_info = Info("app", "Application information", registry=REGISTRY)

# Set app info
app_info.info(
    {
        "version": "1.0.0",
        "name": "babyshield-api",
        "environment": os.getenv("ENVIRONMENT", "production"),
    }
)

# ========================= ROUTER =========================

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

metrics_router = APIRouter(tags=["Metrics"])


# ========================= MIDDLEWARE =========================


# Note: Middleware should be added at the app level, not router level
# This function is kept for reference but not used as middleware
async def track_metrics(request: Request, call_next):
    """Middleware to track request metrics - should be added at app level"""

    # Skip metrics endpoint itself
    if request.url.path == "/metrics":
        return await call_next(request)

    # Start timer
    start_time = time.time()

    # Get request size
    content_length = request.headers.get("content-length")
    if content_length:
        http_request_size_bytes.labels(method=request.method, endpoint=request.url.path).observe(
            int(content_length)
        )

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Track metrics
    http_requests_total.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(
        duration
    )

    # Track errors
    if response.status_code >= 400:
        error_type = "4xx" if response.status_code < 500 else "5xx"
        error_total.labels(type=error_type, endpoint=request.url.path).inc()

    # Track response size
    if hasattr(response, "headers") and "content-length" in response.headers:
        http_response_size_bytes.labels(method=request.method, endpoint=request.url.path).observe(
            int(response.headers["content-length"])
        )

    return response


# ========================= HEALTH CHECKS =========================

# Disabled to avoid conflict with main /healthz endpoint
# @router.get("/healthz")
# async def health_check():
#     """
#     Basic health check - returns 200 if service is up
#     Used by load balancers and Kubernetes liveness probes
#     """
#     return {
#         "status": "healthy",
#         "timestamp": datetime.now().isoformat(),
#         "service": "babyshield-api",
#         "version": "1.0.0"
#     }


@router.get("/readyz")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are ready
    Used by Kubernetes readiness probes
    """

    checks = {
        "database": False,
        "redis": True,  # default true when cache disabled
        "api": True,
        "memory": False,
        "disk": False,
    }

    errors = []

    # Check database
    try:
        from core_infra.database import engine

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            checks["database"] = result.scalar() == 1
    except Exception as e:
        errors.append(f"Database check failed: {str(e)}")

    # Check Redis only if REDIS_URL provided
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            import redis

            r = redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            r.ping()
            checks["redis"] = True
        else:
            # Cache disabled by config
            checks["redis"] = True
    except Exception as e:
        checks["redis"] = False
        errors.append(f"Redis check failed: {str(e)}")

    # Check memory usage
    memory = psutil.virtual_memory()
    if memory.percent < 90:
        checks["memory"] = True
    else:
        errors.append(f"Memory usage high: {memory.percent}%")

    # Check disk usage
    disk = psutil.disk_usage("/")
    if disk.percent < 90:
        checks["disk"] = True
    else:
        errors.append(f"Disk usage high: {disk.percent}%")

    # Overall readiness
    ready = all(checks.values())

    response = {
        "ready": ready,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }

    if errors:
        response["errors"] = errors

    status_code = 200 if ready else 503
    return JSONResponse(content=response, status_code=status_code)


@router.get("/livez")
async def liveness_check():
    """
    Liveness check - minimal check to verify process is alive
    Returns 200 if the service is alive, used for container restarts
    """
    return {"alive": True, "timestamp": datetime.now().isoformat()}


# ========================= METRICS ENDPOINTS =========================


@metrics_router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus exposition format
    """

    # Update system metrics
    memory = psutil.virtual_memory()
    system_memory_usage.set(memory.used)

    cpu_percent = psutil.cpu_percent(interval=0.1)
    system_cpu_usage.set(cpu_percent)

    # Get database pool stats if available
    try:
        from core_infra.database import engine

        pool_status = engine.pool.status()
        # Parse pool status: "Pool size: X  Connections in pool: Y"
        import re

        matches = re.findall(r"\d+", pool_status)
        if len(matches) >= 2:
            active_connections = int(matches[0]) - int(matches[1])
            database_connections_active.set(active_connections)
    except:
        pass

    # Generate metrics
    metrics = generate_latest(REGISTRY)
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


# ========================= SLO TRACKING =========================


class SLOTracker:
    """Tracks Service Level Objectives"""

    def __init__(self):
        self.reset_period = timedelta(days=30)  # 30-day rolling window
        self.data = {
            "uptime": {
                "target": 0.999,  # 99.9%
                "current": 0,
                "total_minutes": 0,
                "downtime_minutes": 0,
                "last_reset": datetime.now(),
            },
            "latency_p95": {
                "target": 0.8,  # 800ms
                "measurements": [],
                "last_reset": datetime.now(),
            },
            "error_rate": {
                "target": 0.001,  # 0.1%
                "total_requests": 0,
                "error_requests": 0,
                "last_reset": datetime.now(),
            },
        }

    def record_uptime(self, is_up: bool):
        """Record uptime status"""
        self.data["uptime"]["total_minutes"] += 1
        if not is_up:
            self.data["uptime"]["downtime_minutes"] += 1

        # Calculate current uptime percentage
        total = self.data["uptime"]["total_minutes"]
        down = self.data["uptime"]["downtime_minutes"]
        self.data["uptime"]["current"] = (total - down) / total if total > 0 else 1.0

    def record_latency(self, latency_seconds: float):
        """Record request latency"""
        self.data["latency_p95"]["measurements"].append(latency_seconds)

        # Keep only last 10000 measurements
        if len(self.data["latency_p95"]["measurements"]) > 10000:
            self.data["latency_p95"]["measurements"] = self.data["latency_p95"]["measurements"][
                -10000:
            ]

    def record_request(self, is_error: bool):
        """Record request and error status"""
        self.data["error_rate"]["total_requests"] += 1
        if is_error:
            self.data["error_rate"]["error_requests"] += 1

    def get_slo_status(self) -> Dict[str, Any]:
        """Get current SLO status"""
        import numpy as np

        # Calculate uptime
        uptime_pct = self.data["uptime"]["current"]
        uptime_ok = uptime_pct >= self.data["uptime"]["target"]

        # Calculate p95 latency
        latencies = self.data["latency_p95"]["measurements"]
        p95_latency = np.percentile(latencies, 95) if latencies else 0
        latency_ok = p95_latency <= self.data["latency_p95"]["target"]

        # Calculate error rate
        total_req = self.data["error_rate"]["total_requests"]
        error_req = self.data["error_rate"]["error_requests"]
        error_rate = error_req / total_req if total_req > 0 else 0
        error_ok = error_rate <= self.data["error_rate"]["target"]

        return {
            "uptime": {
                "target": self.data["uptime"]["target"] * 100,
                "current": uptime_pct * 100,
                "status": "OK" if uptime_ok else "VIOLATION",
                "downtime_minutes": self.data["uptime"]["downtime_minutes"],
            },
            "latency_p95": {
                "target_ms": self.data["latency_p95"]["target"] * 1000,
                "current_ms": p95_latency * 1000,
                "status": "OK" if latency_ok else "VIOLATION",
                "sample_size": len(latencies),
            },
            "error_rate": {
                "target_pct": self.data["error_rate"]["target"] * 100,
                "current_pct": error_rate * 100,
                "status": "OK" if error_ok else "VIOLATION",
                "total_requests": total_req,
                "error_requests": error_req,
            },
            "overall_status": "OK" if (uptime_ok and latency_ok and error_ok) else "VIOLATION",
            "evaluation_window": "30 days",
            "last_updated": datetime.now().isoformat(),
        }


# Global SLO tracker instance
slo_tracker = SLOTracker()


@router.get("/slo")
async def get_slo_status():
    """Get current SLO status"""
    return slo_tracker.get_slo_status()


# ========================= SYNTHETIC PROBES =========================


class SyntheticProbe:
    """Runs synthetic probes against key endpoints"""

    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8001")
        self.timeout = 10
        self.probes = {
            "healthz": {
                "url": f"{self.base_url}/api/v1/monitoring/healthz",
                "method": "GET",
                "expected_status": 200,
            },
            "readyz": {
                "url": f"{self.base_url}/api/v1/monitoring/readyz",
                "method": "GET",
                "expected_status": 200,
            },
            "search": {
                "url": f"{self.base_url}/api/v1/search/advanced",
                "method": "POST",
                "data": {"product": "test", "limit": 1},
                "expected_status": 200,
            },
            "agencies": {
                "url": f"{self.base_url}/api/v1/agencies",
                "method": "GET",
                "expected_status": 200,
            },
        }

    async def run_probe(self, probe_name: str) -> Dict[str, Any]:
        """Run a single synthetic probe"""

        if probe_name not in self.probes:
            return {"error": f"Unknown probe: {probe_name}"}

        probe = self.probes[probe_name]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            start_time = time.time()

            try:
                if probe["method"] == "GET":
                    response = await client.get(probe["url"])
                elif probe["method"] == "POST":
                    response = await client.post(probe["url"], json=probe.get("data", {}))
                else:
                    return {"error": f"Unsupported method: {probe['method']}"}

                duration = time.time() - start_time
                success = response.status_code == probe["expected_status"]

                # Record metrics
                slo_tracker.record_latency(duration)
                slo_tracker.record_request(not success)

                return {
                    "probe": probe_name,
                    "success": success,
                    "status_code": response.status_code,
                    "expected_status": probe["expected_status"],
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat(),
                }

            except Exception as e:
                duration = time.time() - start_time

                # Record failure
                slo_tracker.record_request(True)

                return {
                    "probe": probe_name,
                    "success": False,
                    "error": str(e),
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat(),
                }

    async def run_all_probes(self) -> List[Dict[str, Any]]:
        """Run all synthetic probes"""

        tasks = [self.run_probe(name) for name in self.probes]
        results = await asyncio.gather(*tasks)

        # Check overall health
        all_success = all(r.get("success", False) for r in results)
        slo_tracker.record_uptime(all_success)

        return results


# Global synthetic probe instance
synthetic_probe = SyntheticProbe()


@router.get("/probe/{probe_name}")
async def run_single_probe(probe_name: str):
    """Run a single synthetic probe"""
    return await synthetic_probe.run_probe(probe_name)


@router.get("/probe")
async def run_all_probes():
    """Run all synthetic probes"""
    results = await synthetic_probe.run_all_probes()

    all_success = all(r.get("success", False) for r in results)

    return {
        "overall_success": all_success,
        "probes": results,
        "timestamp": datetime.now().isoformat(),
    }


# ========================= CUSTOM METRICS =========================


def track_barcode_scan(scan_type: str, result: str):
    """Track barcode scan metrics"""
    barcode_scans_total.labels(type=scan_type, result=result).inc()


def track_search_query(query_type: str):
    """Track search query metrics"""
    search_queries_total.labels(type=query_type).inc()


def track_recall_found(severity: str):
    """Track recall found metrics"""
    recalls_found_total.labels(severity=severity).inc()


def track_rate_limit(endpoint: str, user: str, remaining: int):
    """Track rate limit metrics"""
    rate_limit_hits_total.labels(endpoint=endpoint, user=user).inc()
    rate_limit_remaining.labels(endpoint=endpoint, user=user).set(remaining)


def track_cache_hit(cache_type: str):
    """Track cache hit"""
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str):
    """Track cache miss"""
    cache_misses_total.labels(cache_type=cache_type).inc()


def track_cache_size(cache_type: str, size: int):
    """Track cache size"""
    cache_size.labels(cache_type=cache_type).set(size)


def track_database_query(query_type: str, duration: float):
    """Track database query metrics"""
    database_query_duration_seconds.labels(query_type=query_type).observe(duration)
