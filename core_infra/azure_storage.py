"""
Azure Blob Storage Client
Abstraction layer for Azure Blob Storage operations (replaces AWS S3)

Features:
- Upload files to Azure Blob Storage
- Generate SAS URLs for secure access
- Check blob existence
- List blobs in container
- Delete blobs
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, generate_blob_sas

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
        try:
            blob_client = self._get_blob_client(blob_name, container_name)

            # Upload blob with content type and metadata
            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings={"content_type": content_type or "application/octet-stream"} if content_type else None,
                metadata=metadata,
            )

            blob_url = blob_client.url
            logger.info(f"File uploaded to Azure Blob Storage: {blob_name}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload file to Azure Blob Storage: {e}")
            raise

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

    def generate_sas_url(
        self,
        blob_name: str,
        container_name: Optional[str] = None,
        expiry_hours: int = 24,
        permissions: str = "r",
    ) -> str:
        """
        Generate SAS (Shared Access Signature) URL for secure blob access

        Args:
            blob_name: Name of the blob
            container_name: Container name
            expiry_hours: URL expiry time in hours (default 24)
            permissions: Permissions string ('r' = read, 'w' = write, 'd' = delete)

        Returns:
            SAS URL with temporary access token
        """
        try:
            container = container_name or self.container_name
            expiry = datetime.utcnow() + timedelta(hours=expiry_hours)

            # Generate SAS token
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
            return blob_url

        except Exception as e:
            logger.error(f"Failed to generate SAS URL: {e}")
            raise

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
        except Exception as e:
            logger.error(f"Error checking blob existence: {e}")
            return False

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
        try:
            blob_client = self._get_blob_client(blob_name, container_name)
            download_stream = blob_client.download_blob()
            blob_data = download_stream.readall()
            logger.info(f"Downloaded blob: {blob_name} ({len(blob_data)} bytes)")
            return blob_data
        except Exception as e:
            logger.error(f"Failed to download blob: {e}")
            raise

    def delete_blob(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Delete blob from container

        Args:
            blob_name: Name of the blob
            container_name: Container name

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            blob_client = self._get_blob_client(blob_name, container_name)
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete blob: {e}")
            return False

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
        try:
            container_client = self._get_container_client(container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)

            blob_names = [blob.name for blob in blobs]

            if max_results:
                blob_names = blob_names[:max_results]

            return blob_names

        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            return []

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
