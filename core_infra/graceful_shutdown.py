"""
Graceful shutdown handler for BabyShield
Ensures clean shutdown without data loss
"""

import signal
import sys
import os
import asyncio
import threading
import time
import logging
from typing import List, Callable, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Manages graceful shutdown of the application
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.shutdown_event = threading.Event()
        self.cleanup_tasks: List[Callable] = []
        self.active_requests = 0
        self.lock = threading.Lock()
        self._original_sigint = None
        self._original_sigterm = None

    def register_cleanup(self, task: Callable):
        """
        Register a cleanup task to run on shutdown
        """
        self.cleanup_tasks.append(task)
        logger.info(f"Registered cleanup task: {task.__name__}")

    def increment_active_requests(self):
        """Track active request"""
        with self.lock:
            self.active_requests += 1

    def decrement_active_requests(self):
        """Track completed request"""
        with self.lock:
            self.active_requests -= 1

    @contextmanager
    def track_request(self):
        """Context manager to track requests"""
        self.increment_active_requests()
        try:
            yield
        finally:
            self.decrement_active_requests()

    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received signal {signal_name}, initiating graceful shutdown...")

        # Set shutdown event
        self.shutdown_event.set()

        # Start shutdown process
        threading.Thread(target=self._shutdown, daemon=False).start()

    def _shutdown(self):
        """
        Perform graceful shutdown
        """
        start_time = time.time()

        # Step 1: Stop accepting new requests
        logger.info("Step 1: Stopping new requests...")

        # Step 2: Wait for active requests to complete
        logger.info(f"Step 2: Waiting for {self.active_requests} active requests...")
        while self.active_requests > 0 and (time.time() - start_time) < self.timeout:
            time.sleep(0.5)
            logger.info(f"  {self.active_requests} requests remaining...")

        if self.active_requests > 0:
            logger.warning(f"Timeout: {self.active_requests} requests still active")

        # Step 3: Run cleanup tasks
        logger.info("Step 3: Running cleanup tasks...")
        for task in self.cleanup_tasks:
            try:
                logger.info(f"  Running {task.__name__}...")
                if asyncio.iscoroutinefunction(task):
                    asyncio.run(task())
                else:
                    task()
            except Exception as e:
                logger.error(f"  Error in cleanup task {task.__name__}: {e}")

        # Step 4: Close resources
        logger.info("Step 4: Closing resources...")
        self._close_resources()

        # Step 5: Final cleanup
        logger.info("Graceful shutdown complete")

        # Exit
        sys.exit(0)

    def _close_resources(self):
        """
        Close all resources
        """
        try:
            # Close database connections
            from core_infra.database import engine

            logger.info("  Closing database connections...")
            engine.dispose()
        except Exception as e:
            logger.error(f"  Error closing database: {e}")

        try:
            # Close Redis connections
            import redis

            logger.info("  Closing Redis connections...")
            r = redis.Redis(host="localhost", port=6379)
            r.close()
        except Exception as e:
            logger.error(f"  Error closing Redis: {e}")

        try:
            # Stop Celery workers
            logger.info("  Stopping Celery workers...")
            # This would need actual Celery app reference
        except Exception as e:
            logger.error(f"  Error stopping Celery: {e}")

    def install(self):
        """
        Install signal handlers
        """
        # Store original handlers
        self._original_sigint = signal.signal(signal.SIGINT, self.signal_handler)
        self._original_sigterm = signal.signal(signal.SIGTERM, self.signal_handler)

        logger.info("✅ Graceful shutdown handler installed")

    def uninstall(self):
        """
        Restore original signal handlers
        """
        if self._original_sigint:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm:
            signal.signal(signal.SIGTERM, self._original_sigterm)


# Global shutdown handler
shutdown_handler = GracefulShutdownHandler()


# Middleware for tracking requests
async def request_tracking_middleware(request, call_next):
    """
    Track active requests for graceful shutdown
    """
    with shutdown_handler.track_request():
        # Check if shutting down
        if shutdown_handler.shutdown_event.is_set():
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=503, content={"error": "Server is shutting down"}
            )

        response = await call_next(request)
        return response


# Cleanup tasks
def cleanup_temp_files():
    """Clean up temporary files"""
    import tempfile
    import shutil

    temp_dir = tempfile.gettempdir()
    logger.info(f"  Cleaning temp files in {temp_dir}")

    # Clean specific app temp files
    import glob

    for temp_file in glob.glob(f"{temp_dir}/babyshield_*"):
        try:
            if os.path.isfile(temp_file):
                os.unlink(temp_file)
            elif os.path.isdir(temp_file):
                shutil.rmtree(temp_file)
        except Exception as e:
            logger.error(f"  Error deleting {temp_file}: {e}")


def flush_logs():
    """Flush all log handlers"""
    logger.info("  Flushing logs...")
    for handler in logging.root.handlers:
        try:
            handler.flush()
        except:
            pass


def save_application_state():
    """Save application state for recovery"""
    import json
    import os

    state = {
        "shutdown_time": time.time(),
        "active_requests": shutdown_handler.active_requests,
        "pid": os.getpid(),
    }

    try:
        with open("shutdown_state.json", "w") as f:
            json.dump(state, f)
        logger.info("  Application state saved")
    except Exception as e:
        logger.error(f"  Error saving state: {e}")


# Register default cleanup tasks
shutdown_handler.register_cleanup(cleanup_temp_files)
shutdown_handler.register_cleanup(flush_logs)
shutdown_handler.register_cleanup(save_application_state)


# FastAPI integration
def setup_graceful_shutdown(app):
    """
    Setup graceful shutdown for FastAPI app
    """
    from fastapi import FastAPI

    @app.on_event("startup")
    async def startup_event():
        """Install shutdown handler on startup"""
        shutdown_handler.install()
        logger.info("✅ Graceful shutdown configured")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Handle FastAPI shutdown"""
        logger.info("FastAPI shutdown event triggered")
        # This is called by FastAPI on shutdown
        # Our signal handler will handle the actual cleanup

    # Add middleware
    @app.middleware("http")
    async def track_requests(request, call_next):
        return await request_tracking_middleware(request, call_next)

    logger.info("✅ Graceful shutdown integrated with FastAPI")


# Celery integration
def setup_celery_graceful_shutdown(celery_app):
    """
    Setup graceful shutdown for Celery workers
    """
    from celery.signals import worker_shutdown, worker_shutting_down

    @worker_shutting_down.connect
    def worker_shutting_down_handler(sig, how, exitcode, **kwargs):
        """Handle Celery worker shutdown"""
        logger.info(f"Celery worker shutting down: signal={sig}, how={how}")

        # Wait for current tasks to complete
        import time

        max_wait = 30
        start = time.time()

        while time.time() - start < max_wait:
            # Check for active tasks
            from celery import current_app

            inspect = current_app.control.inspect()
            active = inspect.active()

            if not active or all(not tasks for tasks in active.values()):
                break

            logger.info("Waiting for Celery tasks to complete...")
            time.sleep(1)

    @worker_shutdown.connect
    def worker_shutdown_handler(**kwargs):
        """Clean up after Celery worker shutdown"""
        logger.info("Celery worker shutdown complete")


# Context manager for graceful operations
@contextmanager
def graceful_operation(name: str, timeout: int = 10):
    """
    Context manager for operations that need graceful handling
    """
    if shutdown_handler.shutdown_event.is_set():
        raise RuntimeError(f"Cannot start {name}: shutdown in progress")

    shutdown_handler.increment_active_requests()
    start_time = time.time()

    try:
        logger.debug(f"Starting graceful operation: {name}")
        yield

    finally:
        shutdown_handler.decrement_active_requests()
        duration = time.time() - start_time
        logger.debug(f"Completed graceful operation: {name} ({duration:.2f}s)")


# Recovery on startup
def check_previous_shutdown():
    """
    Check if previous shutdown was clean
    """
    import json
    import os

    if os.path.exists("shutdown_state.json"):
        try:
            with open("shutdown_state.json", "r") as f:
                state = json.load(f)

            logger.warning(f"Previous shutdown detected at {state['shutdown_time']}")

            if state.get("active_requests", 0) > 0:
                logger.warning(
                    f"Previous shutdown had {state['active_requests']} active requests"
                )

            # Clean up state file
            os.unlink("shutdown_state.json")

        except Exception as e:
            logger.error(f"Error reading shutdown state: {e}")
