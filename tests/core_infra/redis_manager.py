# C:\Users\rossd\Downloads\RossNetAgents\core_infra\redis_manager.py
# Utility for managing asynchronous Redis connections.

import asyncio
import logging
import os
import time

import redis.asyncio as redis  # Import the async redis client
from dotenv import load_dotenv
from redis.asyncio.connection import ConnectionPool

# Load environment variables from .env file at the project root
try:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_root, ".env"))
    # Uncomment for debugging
    # print(f"Redis Manager: Loading .env from {os.path.join(project_root, '.env')}")
except Exception:
    # Fallback if path calculation fails (e.g., running script directly)
    load_dotenv()
    # print("Redis Manager: Loading .env from current directory or parent.")

# --- Configuration ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)  # Use None if no password is set
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))
REDIS_CONNECTION_TIMEOUT = int(os.getenv("REDIS_CONNECTION_TIMEOUT", 5))  # seconds
REDIS_RETRY_ATTEMPTS = int(os.getenv("REDIS_RETRY_ATTEMPTS", 3))
REDIS_RETRY_DELAY = float(os.getenv("REDIS_RETRY_DELAY", 0.5))  # seconds

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

# --- Connection Pool ---
# Global variable to hold the connection pool once created
_redis_pool: ConnectionPool | None = None
_pool_creation_time = 0  # Track when the pool was created for potential refresh


async def create_redis_pool(force_new=False) -> ConnectionPool:
    """Creates and returns an asynchronous Redis connection pool.

    Args:
        force_new: If True, force creation of a new pool even if one exists
    """
    global _redis_pool, _pool_creation_time

    # Check if we need a new pool
    if _redis_pool is None or force_new:
        logger.info(f"Creating Redis connection pool for {REDIS_HOST}:{REDIS_PORT}, DB: {REDIS_DB}")

        # Close existing pool if forcing new one
        if _redis_pool is not None and force_new:
            logger.info("Closing existing Redis pool before creating new one")
            await _redis_pool.disconnect()
            _redis_pool = None

        # Create new pool with retries
        for attempt in range(REDIS_RETRY_ATTEMPTS):
            try:
                connection_kwargs = {
                    "host": REDIS_HOST,
                    "port": REDIS_PORT,
                    "db": REDIS_DB,
                    "decode_responses": True,
                    "socket_timeout": REDIS_CONNECTION_TIMEOUT,
                    "socket_connect_timeout": REDIS_CONNECTION_TIMEOUT,
                    "max_connections": REDIS_MAX_CONNECTIONS,
                }

                if REDIS_PASSWORD:
                    connection_kwargs["password"] = REDIS_PASSWORD

                logger.debug(
                    f"Redis connection attempt {attempt + 1} with params: {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}",
                )
                _redis_pool = redis.ConnectionPool(**connection_kwargs)

                # Test connection immediately
                async with redis.Redis(connection_pool=_redis_pool) as r:
                    if await r.ping():
                        logger.info("Redis connection pool created and ping successful")
                        _pool_creation_time = time.time()
                        return _redis_pool
                    else:
                        logger.warning("Redis ping returned false, retrying...")

            except (
                redis.ConnectionError,
                redis.RedisError,
                ConnectionRefusedError,
            ) as e:
                logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < REDIS_RETRY_ATTEMPTS - 1:
                    logger.info(f"Retrying in {REDIS_RETRY_DELAY} seconds...")
                    await asyncio.sleep(REDIS_RETRY_DELAY)
                else:
                    logger.critical(f"All Redis connection attempts failed: {e}", exc_info=True)
                    _redis_pool = None
                    raise ConnectionError(
                        f"Could not connect to Redis after {REDIS_RETRY_ATTEMPTS} attempts: {e}",
                    ) from e
            except Exception as e:
                logger.critical(f"Unexpected error creating Redis pool: {e}", exc_info=True)
                _redis_pool = None
                raise

    return _redis_pool


async def get_redis_connection() -> redis.Redis:
    """Gets a Redis connection instance from the pool with error handling.

    If pool creation fails, meaningful errors are raised.
    """
    try:
        pool = await create_redis_pool()  # Ensures pool is created
        if pool is None:
            raise ConnectionError("Redis connection pool is not available")

        # Create client instance using the pool
        logger.debug(f"Getting Redis connection from pool ({REDIS_HOST}:{REDIS_PORT})")
        return redis.Redis(connection_pool=pool)

    except (redis.ConnectionError, ConnectionRefusedError) as e:
        logger.error(f"Unable to get Redis connection: {e}")
        raise ConnectionError(f"Redis server may be down or unreachable: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error getting Redis connection: {e}", exc_info=True)
        raise


async def close_redis_pool():
    """Closes the Redis connection pool gracefully."""
    global _redis_pool, _pool_creation_time
    if _redis_pool:
        logger.info("Closing Redis connection pool...")
        try:
            await _redis_pool.disconnect()
        except Exception as e:
            logger.warning(f"Error closing Redis pool: {e}")
        finally:
            _redis_pool = None
            _pool_creation_time = 0
            logger.info("Redis connection pool closed")


async def check_redis_connection() -> bool:
    """Simple utility to check if Redis is reachable.
    Returns True if connection is successful, False otherwise.
    """
    try:
        redis_conn = await get_redis_connection()
        await redis_conn.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis connection check failed: {e}")
        return False


# --- Example Usage (for testing this module directly) ---
async def _test_redis_connection():
    try:
        logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        print("Testing Redis Connection...")
        print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT} DB={REDIS_DB}")

        if not await check_redis_connection():
            print("Initial connection check failed. Make sure Redis is running.")
            return

        redis_conn = await get_redis_connection()
        print("Got connection object.")

        # Test basic operations
        test_key = "rossnet_redis_test"
        test_value = f"connected_at_{time.time()}"

        # SET operation
        await redis_conn.set(test_key, test_value)
        print(f"SET command successful: {test_key} = {test_value}")

        # GET operation
        value = await redis_conn.get(test_key)
        print(f"GET command successful. Value: {value}")
        assert value == test_value, "Retrieved value doesn't match what was set!"

        # DELETE operation
        await redis_conn.delete(test_key)
        print("DELETE command successful.")

        # Test key not exists
        value = await redis_conn.get(test_key)
        print(f"GET after DELETE returned: {value}")

        print("Redis connection test PASSED.")

    except Exception as e:
        print(f"Redis connection test FAILED: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await close_redis_pool()


if __name__ == "__main__":
    # Run the test function if the script is executed directly
    import asyncio

    asyncio.run(_test_redis_connection())
