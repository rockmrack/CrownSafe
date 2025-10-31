"""
Azure Blob Storage Client
Abstraction layer for Azure Blob Storage operations (replaces AWS S3)

Features:
- Upload files to Azure Blob Storage
- Generate SAS URLs for secure access
- Check blob existence
- List blobs in container
- Delete blobs
- Circuit breaker pattern for resilience
- Retry logic with exponential backoff
- Correlation IDs for distributed tracing
- Enhanced error logging
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

from core_infra.azure_storage_resilience import (
    log_azure_error,
    retry_with_exponential_backoff,
    with_correlation_id,
)

logger = logging.getLogger(__name__)


class AzureBlobStorageClient:
    """
    Azure Blob Storage client for Crown Safe
    Replaces boto3 S3 client with Azure Blob Storage
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        account_name: Optional[str] = None,
        account_key: Optional[str] = None,
        container_name: Optional[str] = None,
    ):
        """
        Initialize Azure Blob Storage client

        Args:
            connection_string: Azure Storage connection string (preferred)
            account_name: Storage account name (alternative to connection_string)
            account_key: Storage account key (alternative to connection_string)
            container_name: Default container name (e.g., 'crownsafe-images')
        """
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = account_key or os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.container_name = container_name or os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-images")

        # Initialize BlobServiceClient
        if self.connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        elif self.account_name and self.account_key:
            account_url = f"https://{self.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=self.account_key)
        elif self.account_name:
            # Use DefaultAzureCredential for managed identity
            account_url = f"https://{self.account_name}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        else:
            raise ValueError(
                "Azure Blob Storage configuration missing. Provide either "
                "AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_NAME"
            )

        logger.info(f"Azure Blob Storage client initialized for container: {self.container_name}")

    def _get_container_client(self, container_name: Optional[str] = None):
        """Get container client for specified container"""
        container = container_name or self.container_name
        return self.blob_service_client.get_container_client(container)

    def _get_blob_client(self, blob_name: str, container_name: Optional[str] = None):
        """Get blob client for specified blob"""
        container = container_name or self.container_name
        return self.blob_service_client.get_blob_client(container=container, blob=blob_name)

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    @with_correlation_id
    def upload_file(
        self,
        file_data: bytes,
        blob_name: str,
        container_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload file to Azure Blob Storage

        Args:
            file_data: File data as bytes
            blob_name: Name of the blob (path in container)
            container_name: Container name (defaults to self.container_name)
            content_type: MIME type (e.g., 'application/pdf', 'image/png')
            metadata: Custom metadata dictionary

        Returns:
            Blob URL

        Raises:
            Exception: If upload fails
        """
        blob_client = self._get_blob_client(blob_name, container_name)

        content_settings_dict = {"content_type": content_type or "application/octet-stream"} if content_type else None

        # Upload blob with content type and metadata
        blob_client.upload_blob(
            file_data,
            overwrite=True,
            content_settings=content_settings_dict,
            metadata=metadata,
        )

        blob_url = blob_client.url
        logger.info(f"File uploaded to Azure Blob Storage: {blob_name}")
        return blob_url

    def upload_file_from_path(
        self,
        file_path: str,
        blob_name: Optional[str] = None,
        container_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload file from local path to Azure Blob Storage

        Args:
            file_path: Path to local file
            blob_name: Name of the blob (defaults to filename)
            container_name: Container name
            content_type: MIME type

        Returns:
            Blob URL
        """
        blob_name = blob_name or os.path.basename(file_path)

        with open(file_path, "rb") as f:
            file_data = f.read()

        return self.upload_file(file_data, blob_name, container_name, content_type)

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    def generate_sas_url(
        self,
        blob_name: str,
        container_name: Optional[str] = None,
        expiry_hours: int = 24,
        permissions: str = "r",
        use_cache: bool = True,
    ) -> str:
        """
        Generate SAS (Shared Access Signature) URL for secure blob access
        Supports Redis caching for improved performance (23h cache TTL)

        Args:
            blob_name: Name of the blob
            container_name: Container name
            expiry_hours: URL expiry time in hours (default 24)
            permissions: Permissions string ('r' = read, 'w' = write, 'd' = delete)
            use_cache: Enable Redis caching (default True)

        Returns:
            SAS URL with temporary access token
        """
        container = container_name or self.container_name

        # Try cache first (if enabled)
        if use_cache:
            try:
                from core_infra.azure_storage_cache import get_cache_manager

                cache_manager = get_cache_manager()
                cached_url = cache_manager.get_cached_sas_url(blob_name, container, permissions)
                if cached_url:
                    logger.debug(f"Returning cached SAS URL for {blob_name}")
                    return cached_url
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}, generating new SAS URL")

        # Generate new SAS token
        expiry = datetime.utcnow() + timedelta(hours=expiry_hours)

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read="r" in permissions, write="w" in permissions),
            expiry=expiry,
        )

        # Construct full URL with SAS token
        blob_url = f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"

        logger.info(f"Generated SAS URL for {blob_name}, expires in {expiry_hours}h")

        # Cache the URL (23h TTL, expires before 24h SAS URL)
        if use_cache:
            try:
                from core_infra.azure_storage_cache import get_cache_manager

                cache_manager = get_cache_manager()
                cache_manager.cache_sas_url(blob_name, container, blob_url, permissions, ttl_hours=23)
            except Exception as e:
                logger.warning(f"Failed to cache SAS URL: {e}")

        return blob_url

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    def blob_exists(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Check if blob exists in container

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            True if blob exists, False otherwise
        """
        try:
            blob_client = self._get_blob_client(blob_name, container_name)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    def head_object(self, blob_name: str, container_name: Optional[str] = None) -> dict:
        """
        Get blob properties (equivalent to S3 head_object)

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            Blob properties dictionary

        Raises:
            ResourceNotFoundError: If blob doesn't exist
        """
        blob_client = self._get_blob_client(blob_name, container_name)
        properties = blob_client.get_blob_properties()

        return {
            "ContentLength": properties.size,
            "ContentType": properties.content_settings.content_type,
            "LastModified": properties.last_modified,
            "Metadata": properties.metadata,
        }

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    @with_correlation_id
    def download_blob(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """
        Download blob content as bytes

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            Blob content as bytes

        Raises:
            Exception: If blob doesn't exist or download fails
        """
        blob_client = self._get_blob_client(blob_name, container_name)
        download_stream = blob_client.download_blob()
        blob_data = download_stream.readall()
        logger.info(f"Downloaded blob: {blob_name} ({len(blob_data)} bytes)")
        return blob_data

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    def delete_blob(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Delete blob from container
        Automatically invalidates cached SAS URLs

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            True if deleted successfully, False otherwise
        """
        container = container_name or self.container_name
        blob_client = self._get_blob_client(blob_name, container)
        blob_client.delete_blob()
        logger.info(f"Deleted blob: {blob_name}")

        # Invalidate cached SAS URLs
        try:
            from core_infra.azure_storage_cache import get_cache_manager

            cache_manager = get_cache_manager()
            cache_manager.invalidate_cache(blob_name, container)
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {blob_name}: {e}")

        return True

    @retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
    @log_azure_error
    def list_blobs(
        self,
        container_name: Optional[str] = None,
        prefix: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> list:
        """
        List blobs in container

        Args:
            container_name: Container name
            prefix: Blob name prefix filter
            max_results: Maximum number of results

        Returns:
            List of blob names
        """
        container_client = self._get_container_client(container_name)
        blobs = container_client.list_blobs(name_starts_with=prefix)

        blob_names = [blob.name for blob in blobs]

        if max_results:
            blob_names = blob_names[:max_results]

        return blob_names

    def get_blob_url(self, blob_name: str, container_name: Optional[str] = None) -> str:
        """
        Get public blob URL (without SAS token)

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            Public blob URL
        """
        container = container_name or self.container_name
        return f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}"

    @staticmethod
    def is_azure_blob_url(url: str) -> bool:
        """
        Check if URL is an Azure Blob Storage URL

        Args:
            url: URL to check

        Returns:
            True if Azure Blob URL, False otherwise
        """
        parsed = urlparse(url)
        return "blob.core.windows.net" in (parsed.netloc or "")


# Convenience function for backward compatibility with S3 code
def get_azure_storage_client(
    container_name: Optional[str] = None,
) -> AzureBlobStorageClient:
    """
    Get configured Azure Blob Storage client

    Args:
        container_name: Override default container name

    Returns:
        AzureBlobStorageClient instance
    """
    return AzureBlobStorageClient(container_name=container_name)
