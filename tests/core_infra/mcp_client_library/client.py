# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_client_library\client.py
# Step: Post-Claude-Review-ClientPy-LogLevel
# Addresses: Changed CLIENT_RECV_RAW_BYTES log level from CRITICAL to DEBUG.

import logging

module_logger = logging.getLogger("MCPClientLibrary")
# Critical log to confirm which version of client.py is loaded (put in __init__ of class)

import asyncio  # noqa: E402
import copy  # noqa: E402
import json  # noqa: E402
import uuid  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional  # noqa: E402

import websockets  # noqa: E402
from tenacity import (  # noqa: E402
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)
from websockets.exceptions import (  # noqa: E402
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidURI,
    WebSocketException,
)  # Explicit import
from websockets.exceptions import (  # noqa: E402
    InvalidStatus as WebsocketsInvalidStatus,
)
from websockets.protocol import State as WebSocketStateEnum  # noqa: E402

from .exceptions import MCPConnectionError, MCPError  # noqa: E402
from .models import MCPHeader, MCPMessage  # noqa: E402

if TYPE_CHECKING:
    from websockets.legacy.protocol import WebSocketCommonProtocol

DEFAULT_RECONNECT_DELAY: int = 5
DEFAULT_MAX_CONNECT_ATTEMPTS: int = 5  # Tenacity will use this for @retry if not overridden by instance
DEFAULT_HEARTBEAT_INTERVAL: int = 30


def before_sleep_log(retry_state: RetryCallState):
    instance_self = retry_state.args[0] if retry_state.args and isinstance(retry_state.args[0], MCPClient) else None
    agent_id_str = instance_self.agent_id if instance_self else "UnknownAgent"

    # Determine max_attempts for logging correctly
    max_attempts_for_log = DEFAULT_MAX_CONNECT_ATTEMPTS  # Default
    if instance_self and hasattr(instance_self, "max_connect_attempts_for_retry_decorator"):
        max_attempts_for_log = instance_self.max_connect_attempts_for_retry_decorator
    elif instance_self and hasattr(instance_self, "max_connect_attempts"):  # Fallback to instance attribute
        max_attempts_for_log = instance_self.max_connect_attempts

    wait_time_for_log = DEFAULT_RECONNECT_DELAY  # Default
    if instance_self and hasattr(instance_self, "reconnect_delay_for_retry_decorator"):
        wait_time_for_log = instance_self.reconnect_delay_for_retry_decorator
    elif instance_self and hasattr(instance_self, "reconnect_delay"):  # Fallback to instance attribute
        wait_time_for_log = instance_self.reconnect_delay

    # If tenacity provides next_action.sleep, use that as it's the actual calculated wait
    if retry_state.next_action and hasattr(retry_state.next_action, "sleep"):
        wait_time_for_log = retry_state.next_action.sleep

    logger_to_use = instance_self.logger if instance_self and hasattr(instance_self, "logger") else module_logger
    logger_to_use.warning(
        f"MCPClient ({agent_id_str}): Connection attempt {retry_state.attempt_number}/{max_attempts_for_log} failed. "
        f"Retrying in {wait_time_for_log:.2f}s. Error: {retry_state.outcome.exception() if retry_state.outcome else 'N/A'}"  # noqa: E501
    )


class MCPClient:
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        mcp_server_url: str,
        message_handler: Callable[[MCPMessage], Any],
        capabilities: Optional[List[Dict[str, Any]]] = None,
        reconnect_delay: int = DEFAULT_RECONNECT_DELAY,
        max_connect_attempts: int = DEFAULT_MAX_CONNECT_ATTEMPTS,
        heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL,
    ):
        if not all([agent_id, agent_name, agent_type, mcp_server_url, message_handler]):
            raise ValueError("agent_id, agent_name, agent_type, mcp_server_url, and message_handler are required.")

        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_type = agent_type
        if not mcp_server_url.endswith(f"/ws/{self.agent_id}"):
            self.ws_url = f"{mcp_server_url.rstrip('/')}/ws/{self.agent_id}"
        else:
            self.ws_url = mcp_server_url

        self.message_handler = message_handler
        self.capabilities = capabilities if capabilities else []

        # Store these for the @retry decorator's before_sleep_log to access if needed
        self.reconnect_delay_for_retry_decorator = reconnect_delay
        self.max_connect_attempts_for_retry_decorator = max_connect_attempts

        self.heartbeat_interval = heartbeat_interval

        self.websocket: Optional["WebSocketCommonProtocol"] = None
        self._is_connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stop_requested = asyncio.Event()
        self.logger = logging.getLogger(f"MCPClient.{self.agent_id}")
        self.logger.critical(
            f"MCPClient INSTANCE LOADED (Post-Claude-Review-ClientPy-LogLevel). Agent: {self.agent_id}"
        )  # Updated version marker
        self.logger.info(
            f"MCPClient initialized for agent '{self.agent_name}' (ID: {self.agent_id}, Type: {self.agent_type}) connecting to {self.ws_url}"  # noqa: E501
        )

    def is_websocket_open(self) -> bool:
        if self.websocket is None:
            return False
        try:
            return self.websocket.state == WebSocketStateEnum.OPEN
        except AttributeError:
            self.logger.error(f"AttributeError accessing websocket.state for {self.agent_id}.")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error checking WebSocket state for {self.agent_id}: {e}",
                exc_info=True,
            )
            return False

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self.is_websocket_open()

    # The @retry decorator needs to use the instance's specific values for attempts and delay
    # One way is to make connect a method that calls a retry-decorated internal method,
    # or ensure the decorator can access instance attributes if tenacity supports it directly.
    # For simplicity, the decorator uses the class-level defaults or values passed at decoration time.
    # If instance-specific retry params are needed for the decorator, it's more complex.
    # The before_sleep_log function now tries to access instance attributes for logging.
    @retry(
        stop=stop_after_attempt(
            DEFAULT_MAX_CONNECT_ATTEMPTS
        ),  # Uses default, not instance specific max_connect_attempts
        wait=wait_fixed(DEFAULT_RECONNECT_DELAY),  # Uses default, not instance specific reconnect_delay
        retry=retry_if_exception_type(
            (
                MCPConnectionError,
                ConnectionRefusedError,
                WebSocketException,
                WebsocketsInvalidStatus,
            )
        ),
        before_sleep=before_sleep_log,
    )
    async def connect(self):
        if self.is_connected:
            self.logger.info(f"Already connected ({self.agent_id}).")
            return
        self.logger.info(f"Attempting to connect to {self.ws_url} ({self.agent_id})...")
        try:
            if self.websocket is not None and not self.is_websocket_open():
                self.logger.debug(f"Clearing previous non-open WebSocket for {self.agent_id}.")
                try:
                    await self.websocket.close()
                except Exception:
                    pass
                self.websocket = None

            # Pass instance-specific timeout to websockets.connect if possible, or use a default
            # For now, using a default timeout for the connection attempt itself.
            connect_timeout = self.reconnect_delay_for_retry_decorator * 1.5  # Example: 1.5x the retry delay
            self.websocket = await asyncio.wait_for(websockets.connect(self.ws_url), timeout=connect_timeout)

            if self.is_websocket_open():
                self._is_connected = True
                self._stop_requested.clear()
                self.logger.info(f"WebSocket connection established successfully for {self.agent_id}.")
                self._receive_task = asyncio.create_task(self._receive_loop())
                self._heartbeat_task = asyncio.create_task(self._send_heartbeat())
            else:
                ws_state_str = str(getattr(self.websocket, "state", "N/A")) if self.websocket else "None"
                self.logger.error(
                    f"connect() for {self.agent_id} completed but WebSocket not OPEN. State: {ws_state_str}"
                )
                if self.websocket:
                    await self.websocket.close()
                self.websocket = None
                self._is_connected = False
                raise MCPConnectionError(f"Failed to establish an OPEN WebSocket connection for {self.agent_id}.")
        except asyncio.TimeoutError:  # Timeout for the websockets.connect call itself
            self._is_connected = False
            self.websocket = None
            self.logger.error(
                f"Connection attempt to {self.ws_url} for {self.agent_id} timed out after {connect_timeout}s."
            )
            raise MCPConnectionError(f"Connection attempt timed out for {self.agent_id}")
        except (
            InvalidURI,
            ConnectionRefusedError,
            WebSocketException,
            WebsocketsInvalidStatus,
        ) as e:
            self._is_connected = False
            self.websocket = None
            if isinstance(e, InvalidURI):
                self.logger.critical(f"Invalid URI for {self.agent_id}: {self.ws_url}")
                raise MCPConnectionError(f"Invalid URI: {self.ws_url}") from e
            elif isinstance(e, ConnectionRefusedError):
                self.logger.error(f"Connection refused by server at {self.ws_url} for {self.agent_id}")
                raise MCPConnectionError(f"Connection refused: {self.ws_url}") from e
            elif isinstance(e, WebsocketsInvalidStatus):
                self.logger.error(
                    f"Server rejected WebSocket for {self.agent_id}: {e.status_code} {e.reason if hasattr(e, 'reason') else 'N/A'}"  # noqa: E501
                )
                raise MCPConnectionError(f"Server rejected WebSocket connection: {e.status_code}") from e
            elif isinstance(e, WebSocketException):
                self.logger.error(
                    f"WebSocket connection failed for {self.agent_id}: {e}",
                    exc_info=True,
                )
                raise MCPConnectionError(f"WebSocket connection failed: {e}") from e
        except Exception as e:
            self._is_connected = False
            self.websocket = None
            self.logger.critical(
                f"Critical unexpected error during connect for {self.agent_id}: {e}",
                exc_info=True,
            )
            raise MCPConnectionError(f"Critical unexpected connection error: {e}") from e

    async def disconnect(self):
        if not self._is_connected and self.websocket is None:
            self.logger.info(f"Already disconnected ({self.agent_id}).")
            return
        self.logger.info(f"Disconnecting ({self.agent_id})...")
        self._stop_requested.set()
        tasks_to_cancel = [t for t in [self._heartbeat_task, self._receive_task] if t and not t.done()]
        for task in tasks_to_cancel:
            task.cancel()
        if tasks_to_cancel:
            self.logger.debug(f"Awaiting cancellation of {len(tasks_to_cancel)} tasks for {self.agent_id}.")
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            self.logger.debug(f"Tasks cancelled for {self.agent_id}.")
        if self.websocket and self.is_websocket_open():
            try:
                await self.websocket.close(code=1000, reason="Client initiated disconnect")
                self.logger.info(f"WebSocket closed gracefully for {self.agent_id}.")
            except Exception as e:
                self.logger.error(f"Error closing WebSocket for {self.agent_id}: {e}", exc_info=True)
        self.websocket = None
        self._is_connected = False
        self._receive_task = None
        self._heartbeat_task = None
        self.logger.info(f"Disconnection process complete for {self.agent_id}.")

    async def send_message(
        self,
        payload: Dict[str, Any],
        message_type: str,
        target_agent_id: Optional[str] = None,
        target_service: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        if not self.is_connected:
            raise MCPConnectionError(f"Cannot send message ({self.agent_id}), not connected.")
        if not message_type:
            raise ValueError("message_type is required.")

        # Use dict.copy() for shallow copy if payload is not deeply nested or modified later by client
        # For safety with potentially complex payloads, deepcopy is safer but has performance cost.
        # Let's assume payload structure is simple enough for dict.copy() or direct use if not modified.
        # If payload can be complex and mutated, deepcopy is better.
        # For now, sticking to deepcopy for safety as payloads can be complex (e.g. 'plan')
        safe_payload = copy.deepcopy(payload)

        header_args = {
            "sender_id": self.agent_id,
            "message_type": message_type,
            "target_agent_id": target_agent_id,
            "target_service": target_service,
        }
        if correlation_id is not None:
            header_args["correlation_id"] = correlation_id

        header = MCPHeader(**header_args)
        message = MCPMessage(mcp_header=header, payload=safe_payload)

        try:
            message_json = message.model_dump_json()
            # Log less for PING to reduce noise
            if message_type == "PING":
                self.logger.debug(f"Sending PING to {target_service or target_agent_id} (CorrID: {correlation_id})")
            else:
                log_message_snippet = message_json[:300] + "..." if len(message_json) > 300 else message_json
                self.logger.debug(f"Sending message ({self.agent_id}): {log_message_snippet}")

            await self.websocket.send(message_json)  # type: ignore

            if message_type == "PING":
                self.logger.debug("Sent PING successfully.")
            else:
                self.logger.info(
                    f"Sent message Type='{message.mcp_header.message_type}', Target='{target_agent_id or target_service}', CorrID='{message.mcp_header.correlation_id}' from {self.agent_id}"  # noqa: E501
                )
        except WebSocketException as e:
            self.logger.error(f"WebSocket error during send ({self.agent_id}): {e}", exc_info=True)
            self._is_connected = False  # Assume connection is lost on send error
            raise MCPConnectionError(f"WebSocket send error ({self.agent_id}): {e}") from e
        except Exception as e:
            self.logger.error(
                f"Failed to send message Type='{message_type}' ({self.agent_id}): {e}",
                exc_info=True,
            )
            raise MCPError(f"Failed to send message ({self.agent_id}): {e}") from e

    async def register_self(self):
        self.logger.info(
            f"Registering {self.agent_id} (Type: {self.agent_type}) with capabilities: {self.capabilities}"
        )
        payload = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "status": "active",
        }
        try:
            await self.send_message(
                payload=payload,
                message_type="DISCOVERY_REGISTER",
                target_service="MCP_DISCOVERY",
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send registration message for {self.agent_id}: {e}",
                exc_info=True,
            )

    async def query_discovery(self, capabilities_to_query: List[str]) -> Optional[str]:
        if not (
            isinstance(capabilities_to_query, list)
            and all(isinstance(c, str) for c in capabilities_to_query)
            and capabilities_to_query
        ):
            self.logger.error(f"Invalid capabilities_to_query for {self.agent_id}: {capabilities_to_query}")
            raise ValueError("capabilities_to_query must be a non-empty list of strings.")
        correlation_id_for_query = str(uuid.uuid4())
        payload = {
            "requester_agent_id": self.agent_id,
            "query_by_capability_list": capabilities_to_query,
        }
        self.logger.info(
            f"Sending discovery query (CorrID: {correlation_id_for_query}) for {capabilities_to_query} from {self.agent_id}"  # noqa: E501
        )
        try:
            await self.send_message(
                payload=payload,
                message_type="DISCOVERY_QUERY",
                target_service="MCP_DISCOVERY",
                correlation_id=correlation_id_for_query,
            )
            return correlation_id_for_query
        except Exception as e:
            self.logger.error(
                f"Failed to send discovery query (CorrID: {correlation_id_for_query}) for {self.agent_id}: {e}",
                exc_info=True,
            )
            return None

    async def _receive_loop(self):
        self.logger.info(f"Receive loop started for {self.agent_id}.")
        while not self._stop_requested.is_set() and self._is_connected:
            if not self.is_websocket_open():
                self.logger.warning(f"Receive loop ({self.agent_id}): WebSocket not open. Breaking loop.")
                self._is_connected = False
                break
            try:
                self.logger.debug(f"Receive loop ({self.agent_id}): Awaiting message...")
                message_text = await asyncio.wait_for(self.websocket.recv(), timeout=self.heartbeat_interval + 10.0)  # type: ignore

                # CHANGED LOG LEVEL FROM CRITICAL TO DEBUG
                self.logger.debug(f"CLIENT_RECV_RAW_BYTES ({self.agent_id}): <<< {str(message_text)[:1000]} >>>")

                message_data = None
                validated_message: Optional[MCPMessage] = None
                try:
                    self.logger.debug(f"CLIENT_RECV_JSON_PARSE_ATTEMPT ({self.agent_id}): Attempting json.loads...")
                    message_data = json.loads(str(message_text))
                    msg_type_for_log = message_data.get("mcp_header", {}).get("message_type", "UNKNOWN_TYPE")
                    corr_id_for_log = message_data.get("mcp_header", {}).get("correlation_id", "NO_CORR_ID")
                    self.logger.info(
                        f"CLIENT_RECV_JSON_SUCCESS ({self.agent_id}): JSON loaded. Type='{msg_type_for_log}', CorrID='{corr_id_for_log}'"  # noqa: E501
                    )

                    self.logger.debug(
                        f"CLIENT_RECV_PYDANTIC_VALIDATE_ATTEMPT ({self.agent_id}): Attempting MCPMessage.model_validate..."  # noqa: E501
                    )
                    validated_message = MCPMessage.model_validate(message_data)
                    self.logger.info(
                        f"CLIENT_RECV_PYDANTIC_SUCCESS ({self.agent_id}): MCPMessage validated. Type='{validated_message.mcp_header.message_type}', CorrID='{validated_message.mcp_header.correlation_id}'"  # noqa: E501
                    )

                    if self.message_handler:
                        self.logger.debug(
                            f"CLIENT_RECV_INVOKE_HANDLER ({self.agent_id}): Invoking handler for Type='{validated_message.mcp_header.message_type}'..."  # noqa: E501
                        )
                        if asyncio.iscoroutinefunction(self.message_handler):
                            asyncio.create_task(self.message_handler(validated_message))
                        else:
                            self.logger.warning(
                                f"Message handler for {self.agent_id} is synchronous. Consider making it async."
                            )
                            self.message_handler(validated_message)
                    else:
                        self.logger.error(
                            f"No message handler configured for {self.agent_id} to handle Type='{validated_message.mcp_header.message_type if validated_message else 'N/A'}'."  # noqa: E501
                        )
                except json.JSONDecodeError as json_err:
                    self.logger.error(
                        f"CLIENT_RECV_JSON_FAIL ({self.agent_id}): {json_err}. Raw: {str(message_text)[:300]}"
                    )
                except Exception as validation_or_handler_err:
                    self.logger.error(
                        f"CLIENT_RECV_VALIDATE_OR_HANDLE_FAIL ({self.agent_id}): {validation_or_handler_err}",
                        exc_info=True,
                    )
                    data_snippet = (
                        str(message_data)[:500] + "..."
                        if message_data and len(str(message_data)) > 500
                        else str(message_data)
                    )
                    self.logger.error(f"CLIENT_RECV_FAIL_DATA ({self.agent_id}): Problematic data: {data_snippet}")
            except asyncio.TimeoutError:
                self.logger.debug(f"Receive loop ({self.agent_id}): Timeout. Checking connection.")
                continue
            except (
                ConnectionClosedOK,
                ConnectionClosedError,
                asyncio.CancelledError,
                WebSocketException,
            ) as e:
                level = logging.INFO if isinstance(e, (ConnectionClosedOK, asyncio.CancelledError)) else logging.ERROR
                self.logger.log(
                    level,
                    f"Receive loop ({self.agent_id}): Connection closed/cancelled: {type(e).__name__} - {e}",
                )
                self._is_connected = False
                break
            except Exception as e:
                self.logger.error(
                    f"Receive loop ({self.agent_id}): Unexpected outer error: {e}",
                    exc_info=True,
                )
                self._is_connected = False
                break
        self.logger.info(
            f"Receive loop ended for {self.agent_id}. Stop: {self._stop_requested.is_set()}, Connected: {self._is_connected}"  # noqa: E501
        )
        if not self._stop_requested.is_set() and not self._is_connected:
            self.logger.error(f"Connection lost unexpectedly for {self.agent_id}.")
            # Here, one might trigger a reconnect attempt if desired for auto-reconnection.
            # For now, it just logs and the client remains disconnected.

    async def _send_heartbeat(self):
        self.logger.info(f"Heartbeat task started for {self.agent_id} (Interval: {self.heartbeat_interval}s).")
        while not self._stop_requested.is_set():
            try:
                await asyncio.wait_for(self._stop_requested.wait(), timeout=self.heartbeat_interval)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                self.logger.info(f"Heartbeat task cancelled during sleep for {self.agent_id}.")
                break
            if self._stop_requested.is_set():
                break
            if not self.is_connected:
                self.logger.warning(f"Heartbeat ({self.agent_id}): Not connected. Stopping heartbeat.")
                break
            try:
                await self.send_message(
                    payload={"client_timestamp": datetime.now(timezone.utc).timestamp()},
                    message_type="PING",
                    target_service="MCP_ROUTER",
                )
                # self.logger.debug(f"Sent PING from {self.agent_id}.") # Already logged by send_message at DEBUG for PING  # noqa: E501
            except asyncio.CancelledError:
                self.logger.info(f"Heartbeat cancelled during PING send for {self.agent_id}.")
                break
            except (MCPConnectionError, MCPError) as e:
                self.logger.error(
                    f"Heartbeat send error for {self.agent_id}: {e}. Connection lost?. Stopping heartbeat."
                )
                self._is_connected = False
                break
            except Exception as e:
                self.logger.error(
                    f"Heartbeat ({self.agent_id}): Unexpected PING send error: {e}",
                    exc_info=True,
                )
                break
        self.logger.info(f"Heartbeat task ended for {self.agent_id}.")
