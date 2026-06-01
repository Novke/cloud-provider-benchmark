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


# Cache jednog backend instance po tipu. Bez ovoga, io_heavy router pravi nov
# backend (a backend nov SDK klijent) na SVAKI request → pod konkurentnoscu to
# dominira merenje (pool/credential init), ne storage performanse. Reuse instance
# + reuse klijenta unutar nje = fer storage poredjenje. Vidi Nalaz #12.
_BACKEND_CACHE: dict[str, StorageBackend] = {}


def get_storage_backend(backend_type: str) -> StorageBackend:
    """
    Factory: vrati (keširан) storage backend instance po tipu.

    Instance se kreira jednom i reuse-uje kroz requestove, da bi se SDK klijent
    (i konekcioni pool / credential) reuse-ovao umesto da se pravi po pozivu.

    Args:
        backend_type: Type of backend to create.
            Supported: "mock", "r2", "s3", "azure_blob", "gcs", "hetzner_storage"

    Returns:
        StorageBackend instance (keširан).

    Raises:
        ValueError: If backend_type is not supported.
    """
    cached = _BACKEND_CACHE.get(backend_type)
    if cached is not None:
        return cached
    backend = _create_storage_backend(backend_type)
    _BACKEND_CACHE[backend_type] = backend
    return backend


def _create_storage_backend(backend_type: str) -> StorageBackend:
    """Konstruise nov backend instance (bez kesiranja)."""
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
            container_name=settings.azure_blob_container_name,
            connection_string=settings.azure_blob_connection_string or None,
            account_url=settings.azure_blob_account_url or None,
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


async def close_storage_backends() -> None:
    """Zatvori i izbaci sve keširane backend-e (oslobodi konekcije)."""
    for backend in _BACKEND_CACHE.values():
        await backend.close()
    _BACKEND_CACHE.clear()


def reset_storage_backend_cache() -> None:
    """Izbaci cache bez async close-a (za test izolaciju)."""
    _BACKEND_CACHE.clear()
