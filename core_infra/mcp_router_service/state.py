# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_router_service\state.py
# CORRECTED: Fixed return values for connection management functions

import logging
from typing import Any

try:
    from .config import logger
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("mcp_router_service.state")
    logger.warning("Could not import logger from .config, using fallback basicConfig.")

# --- State Variables ---
active_connections: dict[str, Any | None] = {}
logger.info("State: In-memory active connections dictionary initialized.")

active_workflows: dict[str, Any] = {}
logger.info("State: In-memory active workflows dictionary initialized.")

# --- Connection Management Functions ---


def add_connection(agent_id: str, websocket: Any) -> bool:
    """Adds a new WebSocket connection to the active state. Returns True on success."""
    if not isinstance(agent_id, str) or not agent_id:
        logger.error("State Error: add_connection called with invalid agent_id.")
        return False

    # If agent already exists, close the old connection first
    if agent_id in active_connections:
        logger.warning(f"State: Agent ID '{agent_id}' already exists in active connections. Replacing old connection.")
        old_ws = active_connections[agent_id]
        if old_ws:
            try:
                # Try to close old connection gracefully
                import asyncio

                if hasattr(old_ws, "close"):
                    asyncio.create_task(old_ws.close(code=1001, reason="Replaced by new connection"))
            except Exception as e:
                logger.debug(f"Error closing old connection for {agent_id}: {e}")

    logger.debug(f"State: Adding connection for agent '{agent_id}'.")
    active_connections[agent_id] = websocket
    return True


def remove_connection(agent_id: str) -> bool:
    """Removes a WebSocket connection from the active state. Returns True if removed."""
    if not isinstance(agent_id, str) or not agent_id:
        logger.error("State Error: remove_connection called with invalid agent_id.")
        return False

    logger.debug(f"State: Attempting to remove connection for agent '{agent_id}'.")
    if agent_id in active_connections:
        del active_connections[agent_id]
        logger.debug(f"State: Connection for agent '{agent_id}' removed.")
        return True
    else:
        logger.warning(f"State: Attempted to remove non-existent connection for agent '{agent_id}'.")
        return False


def get_connection(agent_id: str) -> Any | None:
    """Retrieves a WebSocket connection by agent_id."""
    if not isinstance(agent_id, str) or not agent_id:
        logger.error("State Error: get_connection called with invalid agent_id.")
        return None
    logger.debug(f"State: Getting connection for agent '{agent_id}'.")
    return active_connections.get(agent_id)


def get_all_connections() -> dict[str, Any | None]:
    """Returns the dictionary of all active connections."""
    logger.debug("State: Getting all active connections.")
    return active_connections


async def close_all_connections() -> None:
    """Close all active WebSocket connections."""
    logger.info("State: Closing all active WebSocket connections...")
    for agent_id, websocket in list(active_connections.items()):
        if websocket:
            try:
                await websocket.close(code=1001, reason="Server shutdown")
                logger.debug(f"Closed connection for {agent_id}")
            except Exception as e:
                logger.debug(f"Error closing connection for {agent_id}: {e}")
    active_connections.clear()
    logger.info("State: All connections closed and cleared.")


# --- Workflow State Management Functions ---


def add_workflow(workflow_id: str, initial_state: Any) -> None:
    """Adds a new workflow state."""
    if not isinstance(workflow_id, str) or not workflow_id:
        logger.error("State Error: add_workflow called with invalid workflow_id.")
        return
    if workflow_id in active_workflows:
        logger.warning(f"State: Workflow ID '{workflow_id}' already exists. Overwriting state.")
    logger.debug(f"State: Adding workflow '{workflow_id}'.")
    active_workflows[workflow_id] = initial_state


def update_workflow(workflow_id: str, updated_state: Any) -> None:
    """Updates an existing workflow state."""
    if not isinstance(workflow_id, str) or not workflow_id:
        logger.error("State Error: update_workflow called with invalid workflow_id.")
        return
    if workflow_id in active_workflows:
        logger.debug(f"State: Updating workflow '{workflow_id}'.")
        active_workflows[workflow_id] = updated_state
    else:
        logger.warning(f"State: Attempted to update non-existent workflow '{workflow_id}'.")


def get_workflow(workflow_id: str) -> Any | None:
    """Retrieves a workflow state."""
    if not isinstance(workflow_id, str) or not workflow_id:
        logger.error("State Error: get_workflow called with invalid workflow_id.")
        return None
    logger.debug(f"State: Getting workflow '{workflow_id}'.")
    return active_workflows.get(workflow_id)


def remove_workflow(workflow_id: str) -> None:
    """Removes a workflow state upon completion or failure."""
    if not isinstance(workflow_id, str) or not workflow_id:
        logger.error("State Error: remove_workflow called with invalid workflow_id.")
        return
    logger.debug(f"State: Attempting to remove workflow '{workflow_id}'.")
    if workflow_id in active_workflows:
        del active_workflows[workflow_id]
        logger.debug(f"State: Workflow '{workflow_id}' removed.")
    else:
        logger.warning(f"State: Attempted to remove non-existent workflow '{workflow_id}'.")


logger.info("State module loaded and functions defined.")
