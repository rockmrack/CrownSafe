"""
Async helpers for BabyShield
Prevents timeouts with non-blocking external API calls
"""

import asyncio
import aiohttp
import httpx
from typing import List, Dict, Any, Optional, Callable
from functools import wraps
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class AsyncAPIClient:
    """
    Async HTTP client with timeout, retry, and error handling
    """

    def __init__(self, timeout: int = 30, max_retries: int = 3, backoff_factor: float = 1.0):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()

    async def get(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Async GET request with retry logic
        """
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Async POST request with retry logic
        """
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make async request with retry logic
        """
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                start_time = time.time()

                async with self.session.request(method, url, **kwargs) as response:
                    response_time = time.time() - start_time

                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"API call successful: {method} {url} ({response_time:.2f}s)")
                        return data
                    elif response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        logger.warning(f"API call failed: {method} {url} Status: {response.status}")
                        last_exception = Exception(f"HTTP {response.status}")

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                last_exception = TimeoutError(f"Request timed out after {self.timeout}s")
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                last_exception = e

            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = self.backoff_factor * (2**attempt)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error(f"All retries exhausted for {url}")
        raise last_exception or Exception("Request failed")


async def fetch_multiple_apis(urls: List[str], timeout: int = 30) -> List[Optional[Dict[str, Any]]]:
    """
    Fetch data from multiple APIs concurrently
    """
    async with AsyncAPIClient(timeout=timeout) as client:
        tasks = [client.get(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {urls[i]}: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results


def async_endpoint(func):
    """
    Decorator to convert sync endpoint to async
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # If the function is already async, just call it
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        # Otherwise, run it in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    return wrapper


class AsyncBatchProcessor:
    """
    Process items in batches asynchronously
    """

    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        self.batch_size = batch_size
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process(self, items: List[Any], process_func: Callable) -> List[Any]:
        """
        Process items in concurrent batches
        """
        results = []

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = await self._process_batch(batch, process_func)
            results.extend(batch_results)

            logger.info(
                f"Processed batch {i // self.batch_size + 1}, Total: {len(results)}/{len(items)}"
            )

        return results

    async def _process_batch(self, batch: List[Any], process_func: Callable) -> List[Any]:
        """
        Process a single batch with concurrency limit
        """

        async def process_with_semaphore(item):
            async with self.semaphore:
                if asyncio.iscoroutinefunction(process_func):
                    return await process_func(item)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, process_func, item)

        tasks = [process_with_semaphore(item) for item in batch]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Async cache decorator
def async_cache(ttl: int = 300):
    """
    Cache async function results
    """
    cache = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Check cache
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"Cache hit for {key}")
                    return value

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            cache[key] = (result, time.time())

            return result

        return wrapper

    return decorator


# Convert blocking operations to async
class AsyncConverter:
    """
    Convert blocking database/API calls to async
    """

    @staticmethod
    async def run_sync_in_thread(sync_func: Callable, *args, **kwargs):
        """
        Run synchronous function in thread pool
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)

    @staticmethod
    async def convert_requests_to_async(url: str, method: str = "GET", **kwargs):
        """
        Convert requests library call to async
        """
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            return response.json() if response.status_code == 200 else None


# Example usage functions
async def fetch_recalls_async() -> Dict[str, Any]:
    """
    Example: Fetch recalls from multiple sources concurrently
    """
    urls = [
        "https://api.cpsc.gov/recalls",
        "https://api.fda.gov/drug/enforcement.json",
        "https://api.nhtsa.gov/recalls",
    ]

    results = await fetch_multiple_apis(urls, timeout=30)

    return {"cpsc": results[0], "fda": results[1], "nhtsa": results[2]}


@async_cache(ttl=600)
async def get_product_data_async(barcode: str) -> Dict[str, Any]:
    """
    Example: Get product data with caching
    """
    async with AsyncAPIClient() as client:
        return await client.get(f"https://api.upcitemdb.com/prod/v1/lookup?upc={barcode}")


# Async task queue
class AsyncTaskQueue:
    """
    Simple async task queue for background processing
    """

    def __init__(self, max_workers: int = 10):
        self.queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False

    async def add_task(self, task: Callable, *args, **kwargs):
        """Add task to queue"""
        await self.queue.put((task, args, kwargs))

    async def start(self):
        """Start processing tasks"""
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}")) for i in range(self.max_workers)
        ]

    async def stop(self):
        """Stop processing tasks"""
        self.running = False
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()

    async def _worker(self, name: str):
        """Worker to process tasks"""
        while self.running:
            try:
                task, args, kwargs = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                logger.debug(f"{name} processing task")

                if asyncio.iscoroutinefunction(task):
                    await task(*args, **kwargs)
                else:
                    await asyncio.get_event_loop().run_in_executor(None, task, *args, **kwargs)

                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"{name} error: {e}")
