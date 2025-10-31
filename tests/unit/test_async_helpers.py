"""Unit tests for core_infra/async_helpers.py
Tests async HTTP client, batch processing, caching, and task queue functionality.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from core_infra.async_helpers import (
    AsyncAPIClient,
    AsyncBatchProcessor,
    AsyncConverter,
    AsyncTaskQueue,
    async_cache,
    async_endpoint,
    fetch_multiple_apis,
    fetch_recalls_async,
    get_product_data_async,
)


class TestAsyncAPIClient:
    """Test AsyncAPIClient functionality."""

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test async context manager."""
        async with AsyncAPIClient() as client:
            assert client.session is not None
            assert isinstance(client.session, aiohttp.ClientSession)

        # Session should be closed after context exit
        assert client.session.closed

    @pytest.mark.asyncio
    async def test_get_request_success(self) -> None:
        """Test successful GET request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"test": "data"})

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            async with AsyncAPIClient() as client:
                result = await client.get("https://example.com")

                assert result == {"test": "data"}
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_request_success(self) -> None:
        """Test successful POST request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"created": True})

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            async with AsyncAPIClient() as client:
                result = await client.post("https://example.com", json={"data": "test"})

                assert result == {"created": True}
                mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self) -> None:
        """Test rate limit (429) handling."""
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "5"}

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.return_value = mock_response

            async with AsyncAPIClient(max_retries=1) as client:
                with patch("asyncio.sleep") as mock_sleep:
                    with pytest.raises(Exception):
                        await client.get("https://example.com")

                    # Should sleep for retry-after time
                    mock_sleep.assert_called_with(5)

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test timeout error handling."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.side_effect = asyncio.TimeoutError()

            async with AsyncAPIClient(max_retries=1) as client:
                with pytest.raises(TimeoutError):
                    await client.get("https://example.com")

    @pytest.mark.asyncio
    async def test_retry_logic(self) -> None:
        """Test retry logic with exponential backoff."""
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={"success": True})

        with patch("aiohttp.ClientSession.request") as mock_request:
            mock_request.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_success,
            ]

            async with AsyncAPIClient(max_retries=2) as client:
                with patch("asyncio.sleep") as mock_sleep:
                    result = await client.get("https://example.com")

                    assert result == {"success": True}
                    assert mock_request.call_count == 2
                    # Should sleep once for retry
                    assert mock_sleep.call_count == 1


class TestFetchMultipleAPIs:
    """Test fetch_multiple_apis function."""

    @pytest.mark.asyncio
    async def test_successful_fetch(self) -> None:
        """Test successful fetch from multiple APIs."""
        urls = ["https://api1.com", "https://api2.com"]

        mock_responses = [{"data": "api1"}, {"data": "api2"}]

        with patch("core_infra.async_helpers.AsyncAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_responses
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await fetch_multiple_apis(urls)

            assert len(results) == 2
            assert results[0] == {"data": "api1"}
            assert results[1] == {"data": "api2"}

    @pytest.mark.asyncio
    async def test_partial_failure(self) -> None:
        """Test handling of partial failures."""
        urls = ["https://api1.com", "https://api2.com"]

        mock_responses = [{"data": "api1"}, Exception("API2 failed")]

        with patch("core_infra.async_helpers.AsyncAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_responses
            mock_client_class.return_value.__aenter__.return_value = mock_client

            results = await fetch_multiple_apis(urls)

            assert len(results) == 2
            assert results[0] == {"data": "api1"}
            assert results[1] is None


class TestAsyncEndpoint:
    """Test async_endpoint decorator."""

    @pytest.mark.asyncio
    async def test_async_function(self) -> None:
        """Test decorator with async function."""

        @async_endpoint
        async def async_func() -> str:
            return "async_result"

        result = await async_func()
        assert result == "async_result"

    @pytest.mark.asyncio
    async def test_sync_function(self) -> None:
        """Test decorator with sync function."""

        @async_endpoint
        def sync_func() -> str:
            return "sync_result"

        result = await sync_func()
        assert result == "sync_result"


class TestAsyncBatchProcessor:
    """Test AsyncBatchProcessor functionality."""

    @pytest.mark.asyncio
    async def test_process_items(self) -> None:
        """Test processing items in batches."""
        items = list(range(10))

        async def process_item(item):
            return item * 2

        processor = AsyncBatchProcessor(batch_size=3, max_concurrent=2)
        results = await processor.process(items, process_item)

        assert len(results) == 10
        assert results[0] == 0
        assert results[5] == 10
        assert results[9] == 18

    @pytest.mark.asyncio
    async def test_process_with_exceptions(self) -> None:
        """Test processing with exceptions."""
        items = [1, 2, 3]

        async def process_item(item):
            if item == 2:
                raise ValueError("Test error")
            return item * 2

        processor = AsyncBatchProcessor(batch_size=2)
        results = await processor.process(items, process_item)

        assert len(results) == 3
        assert results[0] == 2
        assert isinstance(results[1], ValueError)
        assert results[2] == 6


class TestAsyncCache:
    """Test async_cache decorator."""

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Test cache hit behavior."""
        call_count = 0

        @async_cache(ttl=300)
        async def cached_func(param) -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        # First call
        result1 = await cached_func("test")
        assert result1 == "result_test"
        assert call_count == 1

        # Second call should hit cache
        result2 = await cached_func("test")
        assert result2 == "result_test"
        assert call_count == 1  # Should not increment

    @pytest.mark.asyncio
    async def test_cache_miss_different_params(self) -> None:
        """Test cache miss with different parameters."""
        call_count = 0

        @async_cache(ttl=300)
        async def cached_func(param) -> str:
            nonlocal call_count
            call_count += 1
            return f"result_{param}"

        # Different parameters should cause cache miss
        result1 = await cached_func("test1")
        result2 = await cached_func("test2")

        assert result1 == "result_test1"
        assert result2 == "result_test2"
        assert call_count == 2


class TestAsyncConverter:
    """Test AsyncConverter functionality."""

    @pytest.mark.asyncio
    async def test_run_sync_in_thread(self) -> None:
        """Test running sync function in thread."""

        def sync_func(x, y):
            return x + y

        result = await AsyncConverter.run_sync_in_thread(sync_func, 2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_convert_requests_to_async(self) -> None:
        """Test converting requests to async."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.request.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await AsyncConverter.convert_requests_to_async("https://example.com")
            assert result == {"data": "test"}


class TestExampleFunctions:
    """Test example usage functions."""

    @pytest.mark.asyncio
    async def test_fetch_recalls_async(self) -> None:
        """Test fetch_recalls_async function."""
        mock_results = [
            {"recalls": "cpsc_data"},
            {"alerts": "fda_data"},
            {"recalls": "nhtsa_data"},
        ]

        with patch("core_infra.async_helpers.fetch_multiple_apis") as mock_fetch:
            mock_fetch.return_value = mock_results

            result = await fetch_recalls_async()

            expected = {
                "cpsc": {"recalls": "cpsc_data"},
                "fda": {"alerts": "fda_data"},
                "nhtsa": {"recalls": "nhtsa_data"},
            }
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_product_data_async(self) -> None:
        """Test get_product_data_async function."""
        mock_response = {"product": "test_product"}

        with patch("core_infra.async_helpers.AsyncAPIClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await get_product_data_async("123456789")
            assert result == {"product": "test_product"}


class TestAsyncTaskQueue:
    """Test AsyncTaskQueue functionality."""

    @pytest.mark.asyncio
    async def test_add_and_process_task(self) -> None:
        """Test adding and processing tasks."""
        processed_tasks = []

        async def test_task(task_id) -> str:
            processed_tasks.append(task_id)
            return f"processed_{task_id}"

        queue = AsyncTaskQueue(max_workers=1)

        # Add tasks
        await queue.add_task(test_task, "task1")
        await queue.add_task(test_task, "task2")

        # Start processing
        await queue.start()

        # Wait a bit for processing
        await asyncio.sleep(0.1)

        # Stop processing
        await queue.stop()

        # Check results
        assert len(processed_tasks) == 2
        assert "task1" in processed_tasks
        assert "task2" in processed_tasks

    @pytest.mark.asyncio
    async def test_task_with_exception(self) -> None:
        """Test task processing with exceptions."""
        processed_tasks = []

        async def failing_task(task_id) -> None:
            if task_id == "fail":
                raise ValueError("Task failed")
            processed_tasks.append(task_id)

        queue = AsyncTaskQueue(max_workers=1)

        # Add tasks including one that fails
        await queue.add_task(failing_task, "success")
        await queue.add_task(failing_task, "fail")

        # Start processing
        await queue.start()

        # Wait for processing
        await asyncio.sleep(0.1)

        # Stop processing
        await queue.stop()

        # Check that successful task was processed
        assert "success" in processed_tasks
        # Failed task should not crash the queue
        assert len(processed_tasks) == 1


if __name__ == "__main__":
    pytest.main([__file__])
