"""Storage service factory and utilities.

This module provides a factory function for creating storage backend instances.
Backend implementations are located in the storage_backends package.

Future backends to be implemented:
- S3Backend (AWS S3)
- AzureBlobBackend (Azure Blob Storage)
- GCSBackend (Google Cloud Storage)
"""

from app.config import settings
from .storage_backends import StorageBackend, MockStorageBackend, R2Backend


def get_storage_backend(backend_type: str) -> StorageBackend:
    """
    Factory function to get storage backend instance.

    Args:
        backend_type: Type of backend to create.
            Supported: "mock", "r2"
            Future: "s3", "azure_blob", "gcs"

    Returns:
        StorageBackend: Instance of the requested backend.

    Raises:
        ValueError: If backend_type is not supported.
    """
    if backend_type == "mock":
        return MockStorageBackend()

    if backend_type == "r2":
        return R2Backend(
            endpoint_url=settings.r2_endpoint_url,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
            bucket_name=settings.r2_bucket_name,
        )

    supported = "mock, r2"
    raise ValueError(
        f"Unsupported storage backend type: '{backend_type}'. "
        f"Supported types: {supported}"
    )
