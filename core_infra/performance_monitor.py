"""
Performance monitoring system for BabyShield
Tracks bottlenecks, metrics, and system performance
"""

import asyncio
import gc
import json
import logging
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a performance metric"""

    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class PerformanceMonitor:
    """
    Central performance monitoring system
    """

    def __init__(self, enable_memory_profiling: bool = False):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timers: Dict[str, float] = {}
        self.counters: Dict[str, int] = defaultdict(int)
        self.enable_memory_profiling = enable_memory_profiling
        self._lock = threading.Lock()

        if enable_memory_profiling:
            tracemalloc.start()

    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        with self._lock:
            self.metrics[metric.name].append(metric)

    def start_timer(self, name: str):
        """Start a timer"""
        self.timers[name] = time.perf_counter()

    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a timer and return elapsed time"""
        if name not in self.timers:
            return None

        elapsed = time.perf_counter() - self.timers[name]
        del self.timers[name]

        # Record as metric
        self.record_metric(
            PerformanceMetric(
                name=f"timer.{name}",
                value=elapsed * 1000,
                unit="ms",  # Convert to milliseconds
            )
        )

        return elapsed

    def increment_counter(self, name: str, value: int = 1):
        """Increment a counter"""
        with self._lock:
            self.counters[name] += value

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        metrics = {
            "cpu": {"percent": cpu_percent, "count": psutil.cpu_count()},
            "memory": {
                "percent": memory.percent,
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "total_gb": memory.total / (1024**3),
            },
            "disk": {
                "percent": disk.percent,
                "free_gb": disk.free / (1024**3),
                "used_gb": disk.used / (1024**3),
                "total_gb": disk.total / (1024**3),
            },
        }

        # Process-specific metrics
        process = psutil.Process()
        metrics["process"] = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / (1024**2),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections()),
        }

        return metrics

    def get_memory_profile(self) -> Optional[Dict]:
        """Get memory profiling data"""
        if not self.enable_memory_profiling:
            return None

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")[:10]

        profile = {
            "total_mb": sum(stat.size for stat in top_stats) / (1024**2),
            "top_allocations": [],
        }

        for stat in top_stats:
            profile["top_allocations"].append(
                {
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size / (1024**2),
                    "count": stat.count,
                }
            )

        return profile

    def get_summary(self, time_window: int = 60) -> Dict[str, Any]:
        """Get performance summary for the last N seconds"""
        cutoff = datetime.utcnow() - timedelta(seconds=time_window)
        summary = {
            "metrics": {},
            "counters": dict(self.counters),
            "system": self.get_system_metrics(),
        }

        # Summarize metrics
        for name, values in self.metrics.items():
            recent = [m for m in values if m.timestamp > cutoff]
            if recent:
                summary["metrics"][name] = {
                    "count": len(recent),
                    "avg": sum(m.value for m in recent) / len(recent),
                    "min": min(m.value for m in recent),
                    "max": max(m.value for m in recent),
                    "unit": recent[0].unit,
                }

        # Add memory profile if enabled
        if self.enable_memory_profiling:
            summary["memory_profile"] = self.get_memory_profile()

        return summary

    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.timers.clear()


# Global monitor instance
monitor = PerformanceMonitor()


# Decorators for performance monitoring
def monitor_performance(name: str = None):
    """
    Decorator to monitor function performance

    Usage:
        @monitor_performance("api_call")
        def my_function():
            ...
    """

    def decorator(func):
        metric_name = name or func.__name__

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000

                monitor.record_metric(
                    PerformanceMetric(
                        name=f"function.{metric_name}",
                        value=elapsed,
                        unit="ms",
                        tags={"status": "success"},
                    )
                )

                return result

            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000

                monitor.record_metric(
                    PerformanceMetric(
                        name=f"function.{metric_name}",
                        value=elapsed,
                        unit="ms",
                        tags={"status": "error", "error_type": type(e).__name__},
                    )
                )

                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                elapsed = (time.perf_counter() - start_time) * 1000

                monitor.record_metric(
                    PerformanceMetric(
                        name=f"function.{metric_name}",
                        value=elapsed,
                        unit="ms",
                        tags={"status": "success"},
                    )
                )

                return result

            except Exception as e:
                elapsed = (time.perf_counter() - start_time) * 1000

                monitor.record_metric(
                    PerformanceMetric(
                        name=f"function.{metric_name}",
                        value=elapsed,
                        unit="ms",
                        tags={"status": "error", "error_type": type(e).__name__},
                    )
                )

                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@contextmanager
def monitor_block(name: str):
    """
    Context manager to monitor a code block

    Usage:
        with monitor_block("database_query"):
            # Your code here
    """
    start_time = time.perf_counter()

    try:
        yield
        elapsed = (time.perf_counter() - start_time) * 1000

        monitor.record_metric(
            PerformanceMetric(
                name=f"block.{name}",
                value=elapsed,
                unit="ms",
                tags={"status": "success"},
            )
        )

    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000

        monitor.record_metric(
            PerformanceMetric(
                name=f"block.{name}",
                value=elapsed,
                unit="ms",
                tags={"status": "error", "error_type": type(e).__name__},
            )
        )

        raise


@asynccontextmanager
async def async_monitor_block(name: str):
    """Async version of monitor_block"""
    start_time = time.perf_counter()

    try:
        yield
        elapsed = (time.perf_counter() - start_time) * 1000

        monitor.record_metric(
            PerformanceMetric(
                name=f"block.{name}",
                value=elapsed,
                unit="ms",
                tags={"status": "success"},
            )
        )

    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000

        monitor.record_metric(
            PerformanceMetric(
                name=f"block.{name}",
                value=elapsed,
                unit="ms",
                tags={"status": "error", "error_type": type(e).__name__},
            )
        )

        raise


class DatabaseQueryMonitor:
    """Monitor database query performance"""

    @staticmethod
    def monitor_query(query_name: str):
        """Decorator to monitor database queries"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with monitor_block(f"db_query.{query_name}"):
                    result = func(*args, **kwargs)

                    # Track result size if applicable
                    if hasattr(result, "__len__"):
                        monitor.record_metric(
                            PerformanceMetric(
                                name=f"db_result_size.{query_name}",
                                value=len(result),
                                unit="rows",
                            )
                        )

                    return result

            return wrapper

        return decorator


class APIEndpointMonitor:
    """Monitor API endpoint performance"""

    @staticmethod
    async def monitor_request(request, call_next):
        """Middleware to monitor API requests"""
        start_time = time.perf_counter()

        # Track request
        monitor.increment_counter(f"api.requests.{request.method}")

        try:
            response = await call_next(request)
            elapsed = (time.perf_counter() - start_time) * 1000

            # Record metrics
            monitor.record_metric(
                PerformanceMetric(
                    name="api.response_time",
                    value=elapsed,
                    unit="ms",
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status": str(response.status_code),
                    },
                )
            )

            # Track status codes
            monitor.increment_counter(f"api.status.{response.status_code}")

            # Add performance headers
            response.headers["X-Response-Time"] = f"{elapsed:.2f}ms"

            return response

        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000

            monitor.record_metric(
                PerformanceMetric(
                    name="api.response_time",
                    value=elapsed,
                    unit="ms",
                    tags={
                        "method": request.method,
                        "path": request.url.path,
                        "status": "error",
                        "error_type": type(e).__name__,
                    },
                )
            )

            monitor.increment_counter("api.errors")
            raise


class BottleneckDetector:
    """Detect performance bottlenecks"""

    def __init__(self, threshold_ms: float = 1000):
        self.threshold_ms = threshold_ms
        self.bottlenecks = []

    def analyze(self, monitor: PerformanceMonitor) -> List[Dict]:
        """Analyze metrics for bottlenecks"""
        bottlenecks = []

        for name, metrics in monitor.metrics.items():
            if metrics:
                avg_time = sum(m.value for m in metrics) / len(metrics)
                max_time = max(m.value for m in metrics)

                if max_time > self.threshold_ms:
                    bottlenecks.append(
                        {
                            "name": name,
                            "avg_time_ms": avg_time,
                            "max_time_ms": max_time,
                            "count": len(metrics),
                            "severity": "high" if max_time > self.threshold_ms * 2 else "medium",
                        }
                    )

        return sorted(bottlenecks, key=lambda x: x["max_time_ms"], reverse=True)


# Performance reporting
class PerformanceReporter:
    """Generate performance reports"""

    @staticmethod
    def generate_report(monitor: PerformanceMonitor) -> str:
        """Generate a text performance report"""
        summary = monitor.get_summary()
        detector = BottleneckDetector()
        bottlenecks = detector.analyze(monitor)

        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE REPORT")
        report.append("=" * 60)

        # System metrics
        report.append("\nSYSTEM METRICS:")
        sys_metrics = summary["system"]
        report.append(f"  CPU: {sys_metrics['cpu']['percent']}%")
        report.append(f"  Memory: {sys_metrics['memory']['percent']}% ({sys_metrics['memory']['used_gb']:.1f}GB used)")
        report.append(f"  Process Memory: {sys_metrics['process']['memory_mb']:.1f}MB")

        # Function metrics
        if summary["metrics"]:
            report.append("\nFUNCTION PERFORMANCE:")
            for name, stats in summary["metrics"].items():
                report.append(f"  {name}:")
                report.append(f"    Calls: {stats['count']}")
                report.append(f"    Avg: {stats['avg']:.2f}{stats['unit']}")
                report.append(f"    Min/Max: {stats['min']:.2f}/{stats['max']:.2f}{stats['unit']}")

        # Bottlenecks
        if bottlenecks:
            report.append("\nBOTTLENECKS DETECTED:")
            for b in bottlenecks[:5]:  # Top 5
                report.append(f"  {b['name']}: {b['max_time_ms']:.2f}ms (severity: {b['severity']})")

        # Counters
        if summary["counters"]:
            report.append("\nCOUNTERS:")
            for name, count in summary["counters"].items():
                report.append(f"  {name}: {count}")

        report.append("=" * 60)

        return "\n".join(report)


# Auto-cleanup old metrics
class MetricsGarbageCollector:
    """Automatically clean old metrics"""

    def __init__(self, monitor: PerformanceMonitor, max_age_minutes: int = 60):
        self.monitor = monitor
        self.max_age = timedelta(minutes=max_age_minutes)
        self.running = False
        self._thread = None

    def start(self):
        """Start garbage collection thread"""
        self.running = True
        self._thread = threading.Thread(target=self._collect, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop garbage collection"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _collect(self):
        """Garbage collection loop"""
        while self.running:
            try:
                cutoff = datetime.utcnow() - self.max_age

                with self.monitor._lock:
                    for name, metrics in self.monitor.metrics.items():
                        # Remove old metrics
                        while metrics and metrics[0].timestamp < cutoff:
                            metrics.popleft()

                # Clean every 5 minutes
                time.sleep(300)

            except Exception as e:
                logger.error(f"Error in metrics GC: {e}")


# Example usage
"""
# In your FastAPI app:
from core_infra.performance_monitor import (
    monitor, 
    APIEndpointMonitor,
    PerformanceReporter
)

# Add monitoring middleware
@app.middleware("http")
async def monitor_performance(request, call_next):
    return await APIEndpointMonitor.monitor_request(request, call_next)

# Monitor specific functions
@monitor_performance("database_query")
def get_user(user_id: int):
    # Your code here
    pass

# Get performance report
@app.get("/api/performance")
async def get_performance_report():
    reporter = PerformanceReporter()
    return {
        "report": reporter.generate_report(monitor),
        "summary": monitor.get_summary()
    }
"""
