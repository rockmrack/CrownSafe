"""Comprehensive tests for Azure Blob Storage client
Tests upload, download, deletion, and SAS URL generation.
"""

import os
import uuid
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.storage.blob import BlobProperties, ContentSettings

from core_infra.azure_storage import AzureBlobStorageClient


@pytest.fixture
def mock_blob_service_client():
    """Mock BlobServiceClient for testing."""
    with patch("core_infra.azure_storage.BlobServiceClient") as mock:
        yield mock


@pytest.fixture
def azure_client(mock_blob_service_client):
    """Create AzureBlobStorageClient with mocked dependencies."""
    with patch.dict(
        os.environ,
        {
            "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;",
            "AZURE_STORAGE_CONTAINER": "test-container",
        },
    ):
        client = AzureBlobStorageClient()
        return client


class TestAzureBlobStorageClient:
    """Test suite for AzureBlobStorageClient."""

    def test_init_with_connection_string(self, mock_blob_service_client) -> None:
        """Test client initialization with connection string."""
        connection_string = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=testkey;"

        with patch.dict(
            os.environ,
            {
                "AZURE_STORAGE_CONNECTION_STRING": connection_string,
                "AZURE_STORAGE_CONTAINER": "test-container",
            },
        ):
            client = AzureBlobStorageClient()

            assert client.connection_string == connection_string
            assert client.container_name == "test-container"
            mock_blob_service_client.from_connection_string.assert_called_once()

    def test_init_with_account_key(self, mock_blob_service_client) -> None:
        """Test client initialization with account name and key."""
        with patch.dict(
            os.environ,
            {
                "AZURE_STORAGE_ACCOUNT_NAME": "testaccount",
                "AZURE_STORAGE_ACCOUNT_KEY": "testkey",
                "AZURE_STORAGE_CONTAINER": "test-container",
            },
        ):
            # Remove connection string
            os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)

            client = AzureBlobStorageClient()

            assert client.account_name == "testaccount"
            assert client.account_key == "testkey"
            mock_blob_service_client.assert_called_once()

    def test_upload_file_success(self, azure_client) -> None:
        """Test successful file upload."""
        # Mock blob client
        mock_blob_client = Mock()
        mock_blob_client.url = "https://test.blob.core.windows.net/container/test.txt"
        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        # Test upload
        file_data = b"Test file content"
        blob_name = "test.txt"
        content_type = "text/plain"

        result = azure_client.upload_file(file_data=file_data, blob_name=blob_name, content_type=content_type)

        # Assertions
        assert result == mock_blob_client.url
        mock_blob_client.upload_blob.assert_called_once()
        call_args = mock_blob_client.upload_blob.call_args

        assert call_args[0][0] == file_data
        assert call_args[1]["overwrite"] is True

    def test_upload_file_with_metadata(self, azure_client) -> None:
        """Test file upload with custom metadata."""
        mock_blob_client = Mock()
        mock_blob_client.url = "https://test.blob.core.windows.net/container/test.txt"
        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        file_data = b"Test content"
        blob_name = "test.txt"
        metadata = {"user_id": "12345", "category": "documents"}

        azure_client.upload_file(file_data=file_data, blob_name=blob_name, metadata=metadata)

        call_args = mock_blob_client.upload_blob.call_args
        assert call_args[1]["metadata"] == metadata

    def test_download_blob_success(self, azure_client) -> None:
        """Test successful blob download."""
        mock_blob_client = Mock()
        mock_download_stream = Mock()
        mock_download_stream.readall.return_value = b"Downloaded content"
        mock_blob_client.download_blob.return_value = mock_download_stream

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        result = azure_client.download_blob("test.txt")

        assert result == b"Downloaded content"
        mock_blob_client.download_blob.assert_called_once()

    def test_download_blob_not_found(self, azure_client) -> None:
        """Test blob download when blob doesn't exist."""
        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        with pytest.raises(ResourceNotFoundError):
            azure_client.download_blob("nonexistent.txt")

    def test_blob_exists_true(self, azure_client) -> None:
        """Test blob_exists returns True for existing blob."""
        mock_blob_client = Mock()
        mock_properties = Mock()
        mock_blob_client.get_blob_properties.return_value = mock_properties

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        result = azure_client.blob_exists("test.txt")

        assert result is True
        mock_blob_client.get_blob_properties.assert_called_once()

    def test_blob_exists_false(self, azure_client) -> None:
        """Test blob_exists returns False for non-existent blob."""
        mock_blob_client = Mock()
        mock_blob_client.get_blob_properties.side_effect = ResourceNotFoundError("Not found")

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        result = azure_client.blob_exists("nonexistent.txt")

        assert result is False

    def test_delete_blob_success(self, azure_client) -> None:
        """Test successful blob deletion."""
        mock_blob_client = Mock()
        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        result = azure_client.delete_blob("test.txt")

        assert result is True
        mock_blob_client.delete_blob.assert_called_once()

    def test_head_object_success(self, azure_client) -> None:
        """Test getting blob properties."""
        mock_blob_client = Mock()

        # Mock blob properties
        mock_properties = Mock(spec=BlobProperties)
        mock_properties.size = 1024
        mock_properties.content_settings = ContentSettings(content_type="text/plain")
        mock_properties.last_modified = datetime(2025, 10, 31, 12, 0, 0)
        mock_properties.metadata = {"user_id": "123"}

        mock_blob_client.get_blob_properties.return_value = mock_properties
        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        result = azure_client.head_object("test.txt")

        assert result["ContentLength"] == 1024
        assert result["ContentType"] == "text/plain"
        assert result["Metadata"] == {"user_id": "123"}
        assert isinstance(result["LastModified"], datetime)

    def test_list_blobs_success(self, azure_client) -> None:
        """Test listing blobs in container."""
        mock_container_client = Mock()

        # Mock blob items
        mock_blob1 = Mock()
        mock_blob1.name = "test1.txt"
        mock_blob2 = Mock()
        mock_blob2.name = "test2.txt"
        mock_blob3 = Mock()
        mock_blob3.name = "test3.txt"

        mock_container_client.list_blobs.return_value = [
            mock_blob1,
            mock_blob2,
            mock_blob3,
        ]

        azure_client._get_container_client = Mock(return_value=mock_container_client)

        result = azure_client.list_blobs()

        assert len(result) == 3
        assert "test1.txt" in result
        assert "test2.txt" in result
        assert "test3.txt" in result

    def test_list_blobs_with_prefix(self, azure_client) -> None:
        """Test listing blobs with prefix filter."""
        mock_container_client = Mock()

        mock_blob1 = Mock()
        mock_blob1.name = "images/photo1.jpg"
        mock_blob2 = Mock()
        mock_blob2.name = "images/photo2.jpg"

        mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]

        azure_client._get_container_client = Mock(return_value=mock_container_client)

        result = azure_client.list_blobs(prefix="images/")

        assert len(result) == 2
        mock_container_client.list_blobs.assert_called_once_with(name_starts_with="images/")

    def test_list_blobs_with_max_results(self, azure_client) -> None:
        """Test listing blobs with max_results limit."""
        mock_container_client = Mock()

        mock_blobs = [Mock(name=f"test{i}.txt") for i in range(10)]
        mock_container_client.list_blobs.return_value = mock_blobs

        azure_client._get_container_client = Mock(return_value=mock_container_client)

        result = azure_client.list_blobs(max_results=5)

        assert len(result) == 5

    @patch("core_infra.azure_storage.generate_blob_sas")
    def test_generate_sas_url_success(self, mock_generate_sas, azure_client) -> None:
        """Test SAS URL generation."""
        mock_generate_sas.return_value = "sig=testsignature&expiry=2025-11-01"

        # Set account name for URL construction
        azure_client.account_name = "testaccount"
        azure_client.account_key = "testkey"

        result = azure_client.generate_sas_url(blob_name="test.txt", expiry_hours=1, permissions="r")

        assert "testaccount.blob.core.windows.net" in result
        assert "test-container/test.txt" in result
        assert "sig=testsignature" in result

        # Verify generate_blob_sas was called with correct parameters
        call_args = mock_generate_sas.call_args[1]
        assert call_args["account_name"] == "testaccount"
        assert call_args["blob_name"] == "test.txt"
        assert call_args["container_name"] == "test-container"

    def test_get_blob_url(self, azure_client) -> None:
        """Test getting public blob URL."""
        azure_client.account_name = "testaccount"

        result = azure_client.get_blob_url("test.txt")

        expected_url = "https://testaccount.blob.core.windows.net/test-container/test.txt"
        assert result == expected_url

    def test_get_blob_url_custom_container(self, azure_client) -> None:
        """Test getting blob URL with custom container."""
        azure_client.account_name = "testaccount"

        result = azure_client.get_blob_url("test.txt", container_name="custom-container")

        expected_url = "https://testaccount.blob.core.windows.net/custom-container/test.txt"
        assert result == expected_url


class TestAzureStorageErrorHandling:
    """Test error handling scenarios."""

    def test_http_response_error_handling(self, azure_client) -> None:
        """Test handling of Azure HttpResponseError."""
        mock_blob_client = Mock()
        error = HttpResponseError(message="Service error")
        error.status_code = 503
        mock_blob_client.upload_blob.side_effect = error

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        with pytest.raises(HttpResponseError):
            azure_client.upload_file(b"test", "test.txt")

    def test_resource_exists_error(self, azure_client) -> None:
        """Test handling when resource already exists."""
        mock_blob_client = Mock()
        mock_blob_client.upload_blob.side_effect = ResourceExistsError("Blob already exists")

        azure_client._get_blob_client = Mock(return_value=mock_blob_client)

        # Should handle gracefully or retry (depending on decorator)
        with pytest.raises(ResourceExistsError):
            azure_client.upload_file(b"test", "test.txt")


class TestAzureStorageIntegration:
    """Integration tests (requires Azurite or actual Azure Storage)
    Skip by default, run with: pytest -m integration.
    """

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires Azurite or Azure Storage")
    def test_upload_download_cycle(self) -> None:
        """Test full upload/download cycle."""
        client = AzureBlobStorageClient()

        # Upload
        test_data = b"Integration test data"
        blob_name = f"integration-test-{uuid.uuid4()}.txt"

        upload_url = client.upload_file(test_data, blob_name, content_type="text/plain")
        assert upload_url

        # Download
        downloaded = client.download_blob(blob_name)
        assert downloaded == test_data

        # Cleanup
        assert client.delete_blob(blob_name)

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires Azurite or Azure Storage")
    def test_sas_url_access(self) -> None:
        """Test SAS URL generation and access."""
        client = AzureBlobStorageClient()

        # Upload test file
        test_data = b"SAS URL test"
        blob_name = f"sas-test-{uuid.uuid4()}.txt"
        client.upload_file(test_data, blob_name)

        # Generate SAS URL
        sas_url = client.generate_sas_url(blob_name, expiry_hours=1)
        assert "sig=" in sas_url

        # Cleanup
        client.delete_blob(blob_name)
