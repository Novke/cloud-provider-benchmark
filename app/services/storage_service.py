"""Storage service factory and utilities.

This module provides a factory function for creating storage backend instances.
Backend implementations are located in the storage_backends package.

Future backends to be implemented:
- S3Backend (AWS S3)
- AzureBlobBackend (Azure Blob Storage)
- GCSBackend (Google Cloud Storage)
- HetznerBackend (Hetzner Object Storage)
- R2Backend (Cloudflare R2)
"""

from .storage_backends import StorageBackend, MockStorageBackend


def get_storage_backend(backend_type: str) -> StorageBackend:
    """
    Factory function to get storage backend instance.

    Args:
        backend_type: Type of backend to create.
            Currently supported: "mock"
            Future: "s3", "azure", "gcs", "hetzner", "r2"

    Returns:
        StorageBackend: Instance of the requested backend.

    Raises:
        ValueError: If backend_type is not supported.

    Example:
        >>> backend = get_storage_backend("mock")
        >>> await backend.write("key", b"data")
        >>> data = await backend.read("key")
    """
    backends = {
        "mock": MockStorageBackend,
        # Future backends will be added here:
        # "s3": S3Backend,
        # "azure": AzureBlobBackend,
        # "gcs": GCSBackend,
        # "hetzner": HetznerBackend,
        # "r2": R2Backend,
    }

    backend_class = backends.get(backend_type)
    if backend_class is None:
        supported = ", ".join(backends.keys())
        raise ValueError(
            f"Unsupported storage backend type: '{backend_type}'. "
            f"Supported types: {supported}"
        )

    return backend_class()
