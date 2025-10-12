# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_router_service\main.py
# CORRECTED: Fixed WebSocket connection bugs causing policy violations

import asyncio
import signal
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# --- Environment & Path Setup ---
project_root_main_py = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
env_path = os.path.join(project_root_main_py, ".env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
bootstrap_logger = logging.getLogger("MCPRouterService_Bootstrap")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    bootstrap_logger.info(f"Loaded .env from: {env_path}")
else:
    bootstrap_logger.warning(
        f".env file not found at {env_path}. Service may rely on environment variables being set externally."
    )

# --- Local Module Imports ---
try:
    from .config import logger, settings
    from . import state
    from . import discovery
    from .router import handle_message

    bootstrap_logger.info(
        "Successfully imported local modules (config, state, discovery, router)."
    )
except ImportError as e:
    bootstrap_logger.critical(
        f"CRITICAL IMPORT ERROR: Failed to import local modules: {e}. Check module structure, PYTHONPATH, or if running from the correct directory.",
        exc_info=True,
    )
    sys.exit(f"Import failure: {e}. MCPRouterService cannot start.")


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MCP Router Service: Lifespan startup sequence initiated...")
    try:
        # Initialize or clear agent registry
        if hasattr(discovery, "initialize_registry") and callable(
            discovery.initialize_registry
        ):
            discovery.initialize_registry()
            logger.info(
                "Lifespan: In-memory agent registry explicitly initialized via initialize_registry()."
            )
        elif hasattr(discovery, "agent_registry") and isinstance(
            discovery.agent_registry, dict
        ):
            discovery.agent_registry.clear()
            logger.info(
                "Lifespan: In-memory agent registry cleared via agent_registry.clear()."
            )
        else:
            logger.warning(
                "Lifespan: Agent registry not found or not a dict in discovery module. Cannot clear/initialize."
            )

        # Clear any existing connections from a previous unclean shutdown
        if hasattr(state, "close_all_connections") and callable(
            state.close_all_connections
        ):
            await state.close_all_connections()
            logger.info(
                "Lifespan: Cleared any stale connections via close_all_connections()."
            )
        elif hasattr(state, "active_connections") and isinstance(
            state.active_connections, dict
        ):
            state.active_connections.clear()
            logger.info(
                "Lifespan: Cleared stale connections via active_connections.clear()."
            )

        logger.info("Lifespan: Startup tasks completed.")
    except Exception as startup_e:
        logger.critical(
            f"Lifespan: CRITICAL ERROR during startup initialization: {startup_e}",
            exc_info=True,
        )

    yield

    # Shutdown
    logger.info("MCP Router Service: Lifespan shutdown sequence initiated...")
    try:
        if hasattr(state, "close_all_connections") and callable(
            state.close_all_connections
        ):
            logger.info(
                "Lifespan: Attempting to close all active WebSocket connections..."
            )
            await state.close_all_connections()
            logger.info("Lifespan: All active WebSocket connections closed.")
        else:
            logger.info(
                "Lifespan: state.close_all_connections not found or not callable. Manual connection cleanup might be needed if connections persist."
            )

        logger.info("Lifespan: Resource cleanup during shutdown completed.")
    except Exception as shutdown_e:
        logger.error(
            f"Lifespan: Error during shutdown resource cleanup: {shutdown_e}",
            exc_info=True,
        )
    logger.info("MCP Router Service shutdown complete.")


# --- FastAPI App Initialization ---
SERVICE_NAME = getattr(settings, "SERVICE_NAME", "MCP_Router_Service")
app_logger = (
    logger
    if "logger" in locals() and isinstance(logger, logging.Logger)
    else bootstrap_logger
)

app = FastAPI(
    title=SERVICE_NAME,
    version=getattr(settings, "VERSION", "1.1.0"),
    lifespan=lifespan,
)
app_logger.info(f"{SERVICE_NAME} FastAPI application initialized.")

# --- CORS Middleware ---
cors_origins = getattr(settings, "CORS_ORIGINS", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app_logger.info(f"CORS Middleware added. Allowed Origins: {cors_origins}")


# --- WebSocket Endpoint ---
@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    # Validate required functions exist
    if (
        not (hasattr(state, "add_connection") and callable(state.add_connection))
        or not (
            hasattr(state, "remove_connection") and callable(state.remove_connection)
        )
        or not (
            hasattr(state, "get_all_connections")
            and callable(state.get_all_connections)
        )
        or not callable(handle_message)
    ):
        app_logger.critical(
            "CRITICAL: state module or handle_message function is not properly initialized/imported. WebSocket endpoint cannot function."
        )
        await websocket.accept()
        await websocket.close(code=1011, reason="Server configuration error.")
        return

    await websocket.accept()
    app_logger.info(
        f"Agent '{agent_id}' attempting connection from {websocket.client.host}:{websocket.client.port}"
    )

    # FIXED: Properly check return value of add_connection
    connection_added = state.add_connection(agent_id, websocket)
    if not connection_added:
        app_logger.warning(
            f"Failed to add connection for agent '{agent_id}', invalid agent_id or other error. Closing."
        )
        await websocket.close(code=1008, reason="Failed to register connection.")
        return

    app_logger.info(
        f"WebSocket for agent '{agent_id}' accepted and added. Total connections: {len(state.get_all_connections())}"
    )

    try:
        while True:
            message_text = await websocket.receive_text()
            # FIXED: Remove extra app_logger parameter
            await handle_message(agent_id, message_text, websocket)
    except WebSocketDisconnect as e:
        app_logger.info(
            f"Agent '{agent_id}' disconnected (Code: {e.code}, Reason: '{e.reason if e.reason else 'N/A'}')."
        )
    except Exception as e:
        app_logger.error(
            f"Unexpected error in WebSocket loop for agent '{agent_id}': {type(e).__name__} - {e}",
            exc_info=True,
        )
        if websocket.client_state != websocket.client_state.DISCONNECTED:
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except RuntimeError:
                app_logger.warning(
                    f"RuntimeError attempting to close WebSocket for '{agent_id}', likely already closed."
                )
    finally:
        # FIXED: Properly handle return value
        removed = state.remove_connection(agent_id)
        if removed:
            app_logger.info(
                f"Connection for '{agent_id}' cleanly removed. Total connections: {len(state.get_all_connections())}"
            )
        else:
            app_logger.info(
                f"Attempted to remove connection for '{agent_id}', but it was not found. Total connections: {len(state.get_all_connections())}"
            )


# --- Root Endpoint ---
@app.get("/")
async def read_root():
    app_logger.debug("Root endpoint '/' requested.")
    try:
        active_conn_count = (
            len(state.get_all_connections())
            if hasattr(state, "get_all_connections")
            else "N/A"
        )
        reg_agent_count = (
            len(discovery.agent_registry)
            if hasattr(discovery, "agent_registry")
            else "N/A"
        )
    except Exception:
        active_conn_count = "Error"
        reg_agent_count = "Error"
    return {
        "service_name": SERVICE_NAME,
        "version": getattr(settings, "VERSION", "1.1.0"),
        "status": "Operational",
        "active_websocket_connections": active_conn_count,
        "registered_agents_in_discovery": reg_agent_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- health endpoints for ALB ---
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/healthz", tags=["system"])
async def healthz():
    return {"status": "ok"}


# --- Main execution block ---
if __name__ == "__main__":
    import uvicorn

    main_execution_logger = (
        logger
        if "logger" in locals() and isinstance(logger, logging.Logger)
        else bootstrap_logger
    )

    main_execution_logger.info("Starting MCP Router Service directly using Uvicorn...")

    run_host = getattr(settings, "HOST", "0.0.0.0")
    run_port = getattr(settings, "PORT", 8001)
    run_log_level = getattr(settings, "LOG_LEVEL", "info").lower()
    run_reload = False  # PERMANENTLY DISABLED HOT-RELOAD

    main_execution_logger.info(
        f"Uvicorn configured to run on host='{run_host}', port={run_port}, log_level='{run_log_level}', reload={run_reload}"
    )

    uvicorn.run(
        "core_infra.mcp_router_service.main:app",
        host=run_host,
        port=run_port,
        log_level=run_log_level,
        reload=run_reload,
    )
