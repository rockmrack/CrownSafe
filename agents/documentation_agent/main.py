"""
DocumentationAgent Main Entry Point
Enhanced version with comprehensive features for production deployment
"""

import asyncio
import os
import signal
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import platform
import psutil
from enum import Enum
from dotenv import load_dotenv

# Ensure project root is in sys.path for core_infra imports
project_root_main = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root_main not in sys.path:
    sys.path.insert(0, project_root_main)

try:
    from core_infra.mcp_client_library.client import MCPClient
    from core_infra.mcp_client_library.models import MCPMessage, MCPHeader
    from core_infra.mcp_client_library.config import Settings as MCPConfig
    from core_infra.mcp_client_library.exceptions import MCPConnectionError
except ImportError as e:
    print(f"CRITICAL_ERROR_DOCUMENTATION_MAIN: Failed to import core_infra: {e}")
    sys.exit(1)

# Import agent logic
try:
    from agents.documentation_agent.agent_logic import DocumentationAgentLogic
except ImportError:
    try:
        from .agent_logic import DocumentationAgentLogic
    except ImportError as e:
        print(f"CRITICAL_ERROR_DOCUMENTATION_MAIN: Failed to import agent_logic: {e}")
        sys.exit(1)


# Environment setup
def setup_environment():
    """Setup environment variables with proper fallback"""
    dotenv_paths = [os.path.join(project_root_main, ".env"), ".env"]

    for dotenv_path in dotenv_paths:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            return dotenv_path

    load_dotenv()  # Final fallback
    return "default locations"


# Enhanced logging configuration
def setup_logging():
    """Setup comprehensive logging configuration"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"documentation_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
    )
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,  # 10MB
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return logging.getLogger(__name__)


env_source = setup_environment()


# Configuration with environment variable support
class Config:
    AGENT_ID = os.getenv("DOCUMENTATION_AGENT_ID", "documentation_agent_01")
    AGENT_NAME = "DocumentationAgent"
    AGENT_TYPE = "DocumentationAgent"
    AGENT_VERSION = "2.0-ENHANCED"
    HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
    MAX_RETRIES = int(os.getenv("DOCUMENTATION_MAX_RETRIES", "10"))
    RETRY_DELAY = float(os.getenv("DOCUMENTATION_RETRY_DELAY", "2.0"))
    MAX_RETRY_DELAY = float(os.getenv("DOCUMENTATION_MAX_RETRY_DELAY", "60.0"))
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    ENABLE_HEALTH_CHECK = os.getenv("ENABLE_HEALTH_CHECK", "true").lower() == "true"
    MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "5"))
    CONNECTION_HEALTH_CHECK_INTERVAL = int(os.getenv("DOCUMENTATION_HEALTH_CHECK", "30"))
    STARTUP_DELAY = float(os.getenv("DOCUMENTATION_STARTUP_DELAY", "5.0"))


# Initialize enhanced logger
logger = setup_logging()
logic_logger = logging.getLogger(f"{Config.AGENT_ID}.logic")


class AgentStatus(Enum):
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PROCESSING = "processing"
    IDLE = "idle"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


# Global instances
mcp_client_instance: Optional[MCPClient] = None
agent_logic_instance: Optional[DocumentationAgentLogic] = None


class DocumentationAgentManager:
    """Enhanced Documentation Agent with robust error handling, monitoring, and scaling capabilities"""

    def __init__(self):
        self.agent_id = Config.AGENT_ID
        self.version = Config.AGENT_VERSION
        self.mcp_client: Optional[MCPClient] = None
        self.documentation_logic: Optional[DocumentationAgentLogic] = None
        self.status = AgentStatus.INITIALIZING
        self.is_running = False
        self.start_time = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False

        # Task management
        self.active_tasks = {}
        self.task_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TASKS)
        self.task_count = 0
        self.error_count = 0
        self.last_error = None
        self.connection_retry_count = 0
        self.last_successful_connection = None
        self._health_check_task: Optional[asyncio.Task] = None

        # Capabilities registry - INCLUDING build_final_report for workflow compatibility
        self.capabilities_registry = {
            "build_final_report": {
                "handler": self.handle_generate_docs,
                "description": "Build final consolidated report as requested by workflow",
                "version": "2.0",
            },
            "generate_documentation": {
                "handler": self.handle_generate_docs,
                "description": "Generate PA summary PDF and Letter of Medical Necessity",
                "version": "2.0",
            },
            "generate_pa_summary": {
                "handler": self.handle_pa_summary,
                "description": "Generate PA summary PDF only",
                "version": "2.0",
            },
            "generate_necessity_letter": {
                "handler": self.handle_necessity_letter,
                "description": "Generate Letter of Medical Necessity only",
                "version": "2.0",
            },
            "generate_combined_report": {
                "handler": self.handle_combined_report,
                "description": "Generate comprehensive combined report",
                "version": "2.0",
            },
            "get_agent_status": {
                "handler": self.handle_get_status,
                "description": "Get current agent status and metrics",
                "version": "1.0",
            },
        }

        # Performance metrics
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_processing_time": 0,
            "total_processing_time": 0,
            "tasks_by_type": {},
            "errors_by_type": {},
            "peak_concurrent_tasks": 0,
            "system_metrics": {},
        }

        logger.info(f"Initializing {self.agent_id} v{self.version}")
        logger.info(f"System: {platform.system()} {platform.release()}")
        logger.info(f"Python: {platform.python_version()}")

    async def handle_incoming_message(self, message: MCPMessage):
        """Handle incoming messages with enhanced processing"""
        if not self.documentation_logic or not self.mcp_client:
            logger.error("Logic/MCPClient instance missing in DocumentationAgent handler")
            return

        try:
            # Extract message details
            header: MCPHeader = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            # Log TASK_ASSIGN reception
            if message_type == "TASK_ASSIGN":
                logger.critical(f"[TASK] TASK_ASSIGN RECEIVED: From {sender_id}, CorrID: {correlation_id}")
                logger.critical(f"[TASK] TASK_PAYLOAD: {message.payload}")

            logger.debug(f"Processing {message_type} from {sender_id} (CorrID: {correlation_id})")

            # Route based on message type
            if message_type == "TASK_ASSIGN":
                await self._handle_task_assign(message)
            elif message_type == "CAPABILITY_QUERY":
                await self._handle_capability_query(message)
            elif message_type == "STATUS_REQUEST":
                await self._handle_status_request(message)
            else:
                logger.warning(f"Unhandled message type: {message_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_message_error(message, e)

    async def _handle_task_assign(self, message: MCPMessage):
        """Handle TASK_ASSIGN messages"""
        header = message.mcp_header
        task_payload = message.payload

        # Determine task type
        task_type = task_payload.get("task_type", "generate_documentation")

        # Get appropriate handler
        capability_info = self.capabilities_registry.get(task_type)
        if not capability_info:
            logger.error(f"Unknown task type: {task_type}")
            await self._send_task_fail(header, f"Unknown task type: {task_type}")
            return

        # Process through appropriate handler
        handler = capability_info["handler"]
        result = await handler(task_payload)

        # Send response
        await self._send_task_response(header, result)

    async def handle_generate_docs(self, task_payload: dict) -> dict:
        """Main handler for documentation generation"""
        return await self._process_task(task_payload, "generate_documentation")

    async def handle_pa_summary(self, task_payload: dict) -> dict:
        """Handler for PA summary generation only"""
        task_payload["document_type"] = "pa_summary_only"
        return await self._process_task(task_payload, "generate_pa_summary")

    async def handle_necessity_letter(self, task_payload: dict) -> dict:
        """Handler for necessity letter generation only"""
        task_payload["document_type"] = "necessity_letter_only"
        return await self._process_task(task_payload, "generate_necessity_letter")

    async def handle_combined_report(self, task_payload: dict) -> dict:
        """Handler for combined report generation"""
        task_payload["document_type"] = "combined_report"
        return await self._process_task(task_payload, "generate_combined_report")

    async def handle_get_status(self, task_payload: dict) -> dict:
        """Handler for status requests"""
        return {
            "status": "success",
            "agent_status": self.status.value,
            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "metrics": self.metrics,
            "active_tasks": len(self.active_tasks),
            "version": self.version,
            "health_status": self._get_health_status(),
        }

    async def _process_task(self, task_payload: dict, task_type: str) -> dict:
        """Process task with enhanced error handling, metrics, and concurrency control"""
        task_id = task_payload.get("task_id", f"task_{datetime.now().timestamp()}")
        start_time = datetime.now()

        # Acquire semaphore for concurrency control
        async with self.task_semaphore:
            logger.info(f"Processing {task_type} task: {task_id}")
            self.status = AgentStatus.PROCESSING

            # Track active task
            self.active_tasks[task_id] = {
                "type": task_type,
                "start_time": start_time,
                "status": "processing",
            }

            # Update peak concurrent tasks
            current_concurrent = len(self.active_tasks)
            if current_concurrent > self.metrics["peak_concurrent_tasks"]:
                self.metrics["peak_concurrent_tasks"] = current_concurrent

            try:
                # Update metrics
                self.task_count += 1
                self.metrics["total_tasks"] += 1
                self.metrics["tasks_by_type"][task_type] = self.metrics["tasks_by_type"].get(task_type, 0) + 1

                # Add metadata to payload
                task_payload["agent_metadata"] = {
                    "agent_id": self.agent_id,
                    "agent_version": self.version,
                    "processing_started": start_time.isoformat(),
                    "task_number": self.task_count,
                    "concurrent_tasks": current_concurrent,
                }

                # Collect system metrics if enabled
                if Config.ENABLE_METRICS:
                    task_payload["system_metrics"] = self._collect_system_metrics()

                # Process the task with timeout
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, self.documentation_logic.process_task, task_payload),
                    timeout=300,  # 5 minute timeout
                )

                # Update success metrics
                processing_time = (datetime.now() - start_time).total_seconds()

                if result.get("status") == "success":
                    self.metrics["successful_tasks"] += 1
                    self._update_processing_time_metrics(processing_time)
                    self.active_tasks[task_id]["status"] = "completed"

                    logger.info(f"Task {task_id} completed successfully in {processing_time:.2f}s")
                else:
                    self.metrics["failed_tasks"] += 1
                    self.error_count += 1
                    self.last_error = result.get("message", "Unknown error")
                    self.active_tasks[task_id]["status"] = "failed"
                    error_type = result.get("error_type", "unknown")
                    self.metrics["errors_by_type"][error_type] = self.metrics["errors_by_type"].get(error_type, 0) + 1

                    logger.error(f"Task {task_id} failed: {self.last_error}")

                # Add processing metadata to result
                result["processing_metadata"] = {
                    "processing_time": processing_time,
                    "agent_id": self.agent_id,
                    "agent_version": self.version,
                    "task_id": task_id,
                }

                return result

            except asyncio.TimeoutError:
                self.error_count += 1
                self.metrics["failed_tasks"] += 1
                self.metrics["errors_by_type"]["timeout"] = self.metrics["errors_by_type"].get("timeout", 0) + 1
                self.active_tasks[task_id]["status"] = "timeout"

                logger.error(f"Task {task_id} timed out after 300 seconds")

                return {
                    "status": "error",
                    "message": "Task processing timed out",
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_type": "timeout",
                }

            except Exception as e:
                self.error_count += 1
                self.metrics["failed_tasks"] += 1
                self.last_error = str(e)
                self.active_tasks[task_id]["status"] = "error"
                error_type = type(e).__name__
                self.metrics["errors_by_type"][error_type] = self.metrics["errors_by_type"].get(error_type, 0) + 1

                logger.error(f"Error processing task {task_id}: {e}", exc_info=True)

                return {
                    "status": "error",
                    "message": f"Task processing failed: {str(e)}",
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_type": error_type,
                }

            finally:
                # Clean up active task
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]

                # Update status
                if not self.active_tasks:
                    self.status = AgentStatus.IDLE

    def _collect_system_metrics(self) -> dict:
        """Collect current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Get current event loop tasks
            try:
                loop = asyncio.get_running_loop()
                active_tasks = len([task for task in asyncio.all_tasks(loop) if not task.done()])
            except:
                active_tasks = 0

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available": memory.available,
                "disk_percent": disk.percent,
                "disk_free": disk.free,
                "active_threads": active_tasks,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Could not collect system metrics: {e}")
            return {}

    def _update_processing_time_metrics(self, processing_time: float):
        """Update processing time metrics"""
        self.metrics["total_processing_time"] += processing_time
        successful_tasks = self.metrics["successful_tasks"]
        if successful_tasks > 0:
            self.metrics["average_processing_time"] = self.metrics["total_processing_time"] / successful_tasks

    def _get_health_status(self) -> str:
        """Determine agent health status"""
        error_rate = (self.error_count / self.task_count * 100) if self.task_count > 0 else 0

        if error_rate > 20:
            return "critical"
        elif error_rate > 10:
            return "degraded"
        elif error_rate > 5:
            return "warning"
        else:
            return "healthy"

    async def _send_task_response(self, original_header: MCPHeader, result: Dict[str, Any]):
        """Send task response"""
        try:
            # Determine response type
            if result.get("status") == "success":
                message_type = "TASK_COMPLETE"
            else:
                message_type = "TASK_FAIL"

            # Prepare payload
            payload = {
                "workflow_id": result.get("workflow_id"),
                "task_id": original_header.correlation_id,
                "agent_id": self.agent_id,
                "result": result,
            }

            await self.mcp_client.send_message(
                payload=payload,
                message_type=message_type,
                target_agent_id=original_header.sender_id,
                correlation_id=original_header.correlation_id,
            )

            logger.info(f"Sent {message_type} response to {original_header.sender_id}")

        except Exception as e:
            logger.error(f"Error sending task response: {e}", exc_info=True)

    async def _send_task_fail(self, original_header: MCPHeader, error_message: str):
        """Send task failure response"""
        try:
            payload = {
                "workflow_id": None,
                "task_id": original_header.correlation_id,
                "agent_id": self.agent_id,
                "error_message": error_message,
            }

            await self.mcp_client.send_message(
                payload=payload,
                message_type="TASK_FAIL",
                target_agent_id=original_header.sender_id,
                correlation_id=original_header.correlation_id,
            )

        except Exception as e:
            logger.error(f"Error sending task fail: {e}", exc_info=True)

    async def _handle_capability_query(self, message: MCPMessage):
        """Handle capability query messages"""
        try:
            capabilities = []
            for cap_name, cap_info in self.capabilities_registry.items():
                capabilities.append(
                    {
                        "name": cap_name,
                        "description": cap_info["description"],
                        "version": cap_info["version"],
                    }
                )

            response_payload = {"agent_id": self.agent_id, "capabilities": capabilities}

            await self.mcp_client.send_message(
                payload=response_payload,
                message_type="CAPABILITY_RESPONSE",
                target_agent_id=message.mcp_header.sender_id,
                correlation_id=message.mcp_header.correlation_id,
            )

        except Exception as e:
            logger.error(f"Error handling capability query: {e}", exc_info=True)

    async def _handle_status_request(self, message: MCPMessage):
        """Handle status request messages"""
        try:
            status_data = await self.handle_get_status({})

            await self.mcp_client.send_message(
                payload=status_data,
                message_type="STATUS_RESPONSE",
                target_agent_id=message.mcp_header.sender_id,
                correlation_id=message.mcp_header.correlation_id,
            )

        except Exception as e:
            logger.error(f"Error handling status request: {e}", exc_info=True)

    async def _handle_message_error(self, message: MCPMessage, error: Exception):
        """Handle errors during message processing"""
        try:
            if not message or not message.mcp_header:
                logger.error("Cannot send error response: message/header missing")
                return

            header = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            if message_type == "TASK_ASSIGN" and sender_id and self.mcp_client:
                workflow_id = None
                task_id = None
                if message.payload and isinstance(message.payload, dict):
                    workflow_id = message.payload.get("workflow_id")
                    task_id = message.payload.get("task_id")

                error_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": f"DocumentationAgent failed to process {message_type}: {str(error)}",
                }

                await self.mcp_client.send_message(
                    payload=error_payload,
                    message_type="TASK_FAIL",
                    target_agent_id=sender_id,
                    correlation_id=correlation_id,
                )

                logger.info(f"Sent TASK_FAIL response for error in {message_type}")

        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}", exc_info=True)

    async def connect_with_retry(self) -> bool:
        """Connect to MCP server with exponential backoff retry logic"""
        logger.info(f"Starting connection attempt for {self.agent_id}")

        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                logger.info(f"[RETRYING] Connection attempt {attempt}/{Config.MAX_RETRIES} for {self.agent_id}")

                # Clear any existing connection state
                if self.mcp_client and hasattr(self.mcp_client, "_is_connected"):
                    self.mcp_client._is_connected = False

                # Attempt connection
                await self.mcp_client.connect()

                if not self.mcp_client.is_connected:
                    raise MCPConnectionError("Connection established but is_connected is False")

                # Register with discovery service
                await self.mcp_client.register_self()

                # Verify connection is still active after registration
                if not self.mcp_client.is_connected:
                    raise MCPConnectionError("Connection lost during registration")

                # Success!
                self.connection_retry_count = 0
                self.last_successful_connection = asyncio.get_event_loop().time()
                logger.info(f"[SUCCESS] {self.agent_id} connected and registered successfully on attempt {attempt}")

                # Start health monitoring
                await self._start_health_monitoring()

                return True

            except Exception as e:
                self.connection_retry_count = attempt
                logger.warning(f"[FAILED] Connection attempt {attempt}/{Config.MAX_RETRIES} failed: {e}")

                if attempt < Config.MAX_RETRIES:
                    # Calculate exponential backoff delay
                    delay = min(
                        Config.RETRY_DELAY * (2 ** (attempt - 1)),
                        Config.MAX_RETRY_DELAY,
                    )
                    logger.info(f"[WAITING] Retrying in {delay:.1f} seconds...")

                    try:
                        await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
                        # If stop_event is set during delay, abort retry attempts
                        if self.stop_event.is_set():
                            logger.info("Stop event set during retry delay, aborting connection attempts")
                            return False
                    except asyncio.TimeoutError:
                        pass  # Normal timeout, continue to next attempt
                else:
                    logger.critical(
                        f"[CRITICAL] All {Config.MAX_RETRIES} connection attempts failed for {self.agent_id}"
                    )

        return False

    async def _start_health_monitoring(self):
        """Start periodic health check to monitor connection stability"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        self._health_check_task = asyncio.create_task(self._connection_health_monitor())
        logger.debug(f"Started connection health monitoring for {self.agent_id}")

    async def _connection_health_monitor(self):
        """Monitor connection health and attempt reconnection if needed"""
        logger.debug(f"Connection health monitor started for {self.agent_id}")

        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(Config.CONNECTION_HEALTH_CHECK_INTERVAL)

                if self.stop_event.is_set():
                    break

                # Check connection status
                if not self.mcp_client or not self.mcp_client.is_connected:
                    logger.warning(
                        f"[ALERT] Connection health check failed for {self.agent_id} - attempting reconnection"
                    )

                    if await self.connect_with_retry():
                        logger.info(f"[SUCCESS] Reconnection successful for {self.agent_id}")
                    else:
                        logger.error(f"[CRITICAL] Reconnection failed for {self.agent_id}")
                        self.stop_event.set()  # Trigger shutdown
                        break
                else:
                    logger.debug(f"[SUCCESS] Connection health check passed for {self.agent_id}")

                    # Send heartbeat with status
                    if hasattr(self.mcp_client, "send_heartbeat"):
                        status_data = {
                            "agent_id": self.agent_id,
                            "version": self.version,
                            "status": self.status.value,
                            "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                            "tasks": {
                                "processed": self.task_count,
                                "active": len(self.active_tasks),
                                "successful": self.metrics["successful_tasks"],
                                "failed": self.metrics["failed_tasks"],
                            },
                            "errors": self.error_count,
                            "last_error": self.last_error,
                            "metrics": self.metrics,
                            "health_status": self._get_health_status(),
                            "system_metrics": self._collect_system_metrics() if Config.ENABLE_METRICS else None,
                        }

                        await self.mcp_client.send_heartbeat(status_data)
                        logger.debug(
                            f"Heartbeat sent - Status: {self.status.value}, Active tasks: {len(self.active_tasks)}"
                        )

            except asyncio.CancelledError:
                logger.debug(f"Health monitor cancelled for {self.agent_id}")
                break
            except Exception as e:
                logger.error(f"Error in connection health monitor: {e}", exc_info=True)

    async def _health_check_server(self):
        """Optional HTTP health check endpoint"""
        if not Config.ENABLE_HEALTH_CHECK:
            return

        try:
            from aiohttp import web

            async def health_handler(request):
                health_data = {
                    "status": self._get_health_status(),
                    "agent_id": self.agent_id,
                    "version": self.version,
                    "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                    "tasks_processed": self.task_count,
                    "active_tasks": len(self.active_tasks),
                }
                return web.json_response(health_data)

            app = web.Application()
            app.router.add_get("/health", health_handler)

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", 8080)
            await site.start()

            logger.info("Health check endpoint started on http://0.0.0.0:8080/health")

        except ImportError:
            logger.warning("aiohttp not installed, health check endpoint disabled")
        except Exception as e:
            logger.warning(f"Could not start health check endpoint: {e}")

    async def _metrics_export_loop(self):
        """Periodically export metrics to file"""
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(300)  # Export every 5 minutes
                self._export_metrics()
            except Exception as e:
                logger.error(f"Metrics export error: {e}")

    def _export_metrics(self):
        """Export metrics to JSON file"""
        try:
            metrics_dir = Path("metrics")
            metrics_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            metrics_file = metrics_dir / f"metrics_{self.agent_id}_{timestamp}.json"

            export_data = {
                "agent_id": self.agent_id,
                "version": self.version,
                "export_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                "status": self.status.value,
                "metrics": self.metrics,
                "health_status": self._get_health_status(),
            }

            with open(metrics_file, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.debug(f"Metrics exported to {metrics_file}")

        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    def _initialize_metrics_collection(self):
        """Initialize system metrics collection"""
        try:
            self.metrics["system_metrics"] = {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage("/").total,
            }
            logger.info("System metrics collection initialized")
        except Exception as e:
            logger.warning(f"Could not initialize system metrics: {e}")

    def get_capabilities(self):
        """Get capabilities in format expected by MCPClient"""
        capabilities = []
        for cap_name, cap_info in self.capabilities_registry.items():
            capabilities.append(
                {
                    "name": cap_name,
                    "description": cap_info["description"],
                    "parameters": {"report_data": "dict", "original_request": "dict"},
                }
            )
        return capabilities

    async def initialize_components(self):
        """Initialize DocumentationAgentLogic and MCPClient"""
        try:
            # Create necessary directories
            for directory in ["logs", "metrics", "temp"]:
                Path(directory).mkdir(exist_ok=True)

            # Initialize DocumentationAgentLogic
            self.documentation_logic = DocumentationAgentLogic(agent_id=self.agent_id)

            # Get MCP server URL
            mcp_settings = MCPConfig()
            base_mcp_server_url = mcp_settings.DEFAULT_ROUTER_URL
            if "/ws/" in base_mcp_server_url:
                base_mcp_server_url = base_mcp_server_url.split("/ws/")[0]

            # Initialize MCPClient with correct parameter names (matching report_builder_agent)
            self.mcp_client = MCPClient(
                agent_id=self.agent_id,
                agent_name=Config.AGENT_NAME,
                agent_type=Config.AGENT_TYPE,
                mcp_server_url=base_mcp_server_url,
                capabilities=self.get_capabilities(),
                message_handler=self.handle_incoming_message,
            )

            # Initialize system metrics collection
            if Config.ENABLE_METRICS:
                self._initialize_metrics_collection()

            self.status = AgentStatus.DISCONNECTED

            logger.info(f"DocumentationAgent components initialized (Version: {self.version})")
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {base_mcp_server_url}")
            logger.info(f"Connection config: Max retries={Config.MAX_RETRIES}, Base delay={Config.RETRY_DELAY}s")

            return True

        except Exception as e:
            logger.critical(
                f"Failed to initialize DocumentationAgent components: {e}",
                exc_info=True,
            )
            self.status = AgentStatus.ERROR
            return False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_running_loop()

            def signal_handler(signum):
                signal_name = signal.Signals(signum).name
                logger.info(f"Received shutdown signal: {signal_name}")
                self.stop_event.set()

            for sig in [signal.SIGINT, signal.SIGTERM]:
                try:
                    loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
                    logger.debug(f"Added signal handler for {signal.Signals(sig).name}")
                except (NotImplementedError, OSError) as e:
                    logger.warning(f"Cannot add signal handler for {signal.Signals(sig).name}: {e}")

        except RuntimeError as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    def _log_capabilities(self):
        """Log agent capabilities in a formatted way"""
        logger.info("=" * 60)
        logger.info("AGENT CAPABILITIES:")
        logger.info("=" * 60)

        for cap_name, cap_info in self.capabilities_registry.items():
            logger.info(f"  - {cap_name} (v{cap_info['version']})")
            logger.info(f"    {cap_info['description']}")

        logger.info("=" * 60)

    async def run_main_loop(self):
        """Main agent event loop with enhanced monitoring"""
        logger.info(f"{self.agent_id} entering main event loop...")

        try:
            # Log initial connection status
            if self.mcp_client and self.mcp_client.is_connected:
                logger.info(f"[SUCCESS] {self.agent_id} main loop starting with active connection")
            else:
                logger.warning(f"[WARNING] {self.agent_id} main loop starting without active connection")

            # Start background tasks
            background_tasks = []

            # Start health check server if enabled
            if Config.ENABLE_HEALTH_CHECK:
                background_tasks.append(asyncio.create_task(self._health_check_server(), name="health_check"))

            # Start metrics export if enabled
            if Config.ENABLE_METRICS:
                background_tasks.append(asyncio.create_task(self._metrics_export_loop(), name="metrics_export"))

            self.status = AgentStatus.IDLE

            # Wait for shutdown signal
            await self.stop_event.wait()
            logger.info("Shutdown signal received in main loop")

            # Cancel background tasks
            for task in background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            logger.error(f"Error in main event loop: {e}", exc_info=True)
            self.status = AgentStatus.ERROR

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.shutdown_complete:
            logger.debug(f"{self.agent_id} shutdown already in progress or complete")
            return

        logger.info(f"Shutting down {self.agent_id}...")
        self.shutdown_complete = True
        self.status = AgentStatus.SHUTTING_DOWN

        try:
            # Cancel health monitoring first
            if self._health_check_task and not self._health_check_task.done():
                logger.debug("Cancelling health check task...")
                self._health_check_task.cancel()
                try:
                    await asyncio.wait_for(self._health_check_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                logger.debug("Health check task cancelled")

            # Wait for active tasks to complete (with timeout)
            if self.active_tasks:
                logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
                await asyncio.wait_for(self._wait_for_active_tasks(), timeout=30)

            # Export final metrics
            if Config.ENABLE_METRICS:
                self._export_metrics()

            # Save final state
            self._save_final_state()

            # Shutdown DocumentationAgentLogic
            if self.documentation_logic and hasattr(self.documentation_logic, "shutdown"):
                logger.debug("Shutting down DocumentationAgentLogic...")
                await self.documentation_logic.shutdown()
                logger.debug("DocumentationAgentLogic shutdown complete")

            # Disconnect MCP client
            if self.mcp_client and self.mcp_client.is_connected:
                logger.debug("Disconnecting MCP client...")
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected")

            logger.info(f"[SUCCESS] {self.agent_id} shutdown complete")

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for active tasks, forcing shutdown")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    async def _wait_for_active_tasks(self):
        """Wait for all active tasks to complete"""
        while self.active_tasks:
            await asyncio.sleep(0.5)

    def _save_final_state(self):
        """Save final agent state for debugging/recovery"""
        try:
            state_file = Path("logs") / f"final_state_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            final_state = {
                "agent_id": self.agent_id,
                "version": self.version,
                "final_status": self.status.value,
                "session_start": self.start_time.isoformat() if self.start_time else None,
                "session_end": datetime.now().isoformat(),
                "total_tasks": self.task_count,
                "final_metrics": self.metrics,
                "last_error": self.last_error,
                "incomplete_tasks": list(self.active_tasks.keys()),
            }

            with open(state_file, "w") as f:
                json.dump(final_state, f, indent=2)

            logger.info(f"Final state saved to {state_file}")

        except Exception as e:
            logger.error(f"Failed to save final state: {e}")


async def main():
    """Main entry point with enhanced startup sequencing"""
    logger.info(f"[STARTING] Starting {Config.AGENT_NAME} (ID: {Config.AGENT_ID}, Version: {Config.AGENT_VERSION})")

    agent_manager = DocumentationAgentManager()
    agent_manager.start_time = datetime.now()
    agent_manager.is_running = True

    # Update global instances for backward compatibility
    global mcp_client_instance, agent_logic_instance

    try:
        # Initialize components
        logger.info("Initializing agent components...")
        if not await agent_manager.initialize_components():
            logger.critical("[FAILED] Failed to initialize agent components")
            return 1

        # Update global references
        mcp_client_instance = agent_manager.mcp_client
        agent_logic_instance = agent_manager.documentation_logic

        # Setup signal handlers
        agent_manager.setup_signal_handlers()

        # Log capabilities
        agent_manager._log_capabilities()

        # Enhanced startup delay to ensure MCP Router is ready
        if Config.STARTUP_DELAY > 0:
            logger.info(f"[WAITING] Waiting {Config.STARTUP_DELAY}s for MCP Router to stabilize...")
            await asyncio.sleep(Config.STARTUP_DELAY)

        # Connect and register with retry logic
        logger.info("Attempting connection to MCP Router...")
        if not await agent_manager.connect_with_retry():
            logger.critical("[FAILED] Failed to connect and register agent after all retries")
            return 1

        logger.info(f"[SUCCESS] {Config.AGENT_ID} successfully connected and ready for tasks")

        # Run main loop
        await agent_manager.run_main_loop()

        return 0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        agent_manager.stop_event.set()
        return 0
    except Exception as e:
        logger.critical(f"[CRITICAL] Unexpected error in main: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Performing final shutdown...")
        await agent_manager.shutdown()


if __name__ == "__main__":
    try:
        # Check Python version
        if sys.version_info < (3, 7):
            print("Error: Python 3.7+ required")
            sys.exit(1)

        # Log startup information
        logger.info("=" * 60)
        logger.info("DOCUMENTATION AGENT STARTING")
        logger.info("=" * 60)

        exit_code = asyncio.run(main())
        logger.info(f"[EXITING] {Config.AGENT_NAME} exiting with code {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info(f"[STOPPED] {Config.AGENT_NAME} interrupted")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"[CRITICAL] Fatal error: {e}", exc_info=True)
        sys.exit(1)
