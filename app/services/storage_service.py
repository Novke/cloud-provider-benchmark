"""Storage service factory and utilities."""

from app.config import settings
from .storage_backends import (
    StorageBackend,
    MockStorageBackend,
    S3CompatibleBackend,
    R2Backend,
    AzureBlobBackend,
    GCSBackend,
)


def get_storage_backend(backend_type: str) -> StorageBackend:
    """
    Factory function to get storage backend instance.

    Args:
        backend_type: Type of backend to create.
            Supported: "mock", "r2", "s3", "azure_blob", "gcs"

    Returns:
        StorageBackend instance.

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

    if backend_type == "s3":
        return S3CompatibleBackend(
            bucket_name=settings.s3_bucket_name,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
        )

    if backend_type == "azure_blob":
        return AzureBlobBackend(
            connection_string=settings.azure_blob_connection_string,
            container_name=settings.azure_blob_container_name,
        )

    if backend_type == "gcs":
        return GCSBackend(
            bucket_name=settings.gcs_bucket_name,
            credentials_path=settings.gcs_credentials_path or None,
        )

    if backend_type == "hetzner_storage":
        return S3CompatibleBackend(
            bucket_name=settings.hetzner_storage_bucket_name,
            access_key_id=settings.hetzner_storage_access_key_id,
            secret_access_key=settings.hetzner_storage_secret_access_key,
            region_name=settings.hetzner_storage_region,
            endpoint_url=settings.hetzner_storage_endpoint_url,
        )

    supported = "mock, r2, s3, azure_blob, gcs, hetzner_storage"
    raise ValueError(
        f"Unsupported storage backend type: '{backend_type}'. "
        f"Supported types: {supported}"
    )
