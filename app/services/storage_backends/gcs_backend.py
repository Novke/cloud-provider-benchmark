"""Google Cloud Storage backend."""

import asyncio

from .base import StorageBackend


class GCSBackend(StorageBackend):
    """
    Google Cloud Storage backend using gcloud-aio-storage.

    Used as native storage backend when running on GCP (GCE, Cloud Run, Cloud Functions).
    Uses Application Default Credentials (ADC) when credentials_path is not provided,
    which works automatically on GCP compute environments.

    Storage klijent se kreira JEDNOM (lazy) i reuse-uje. Raniji kod je pravio nov
    `Storage()` (sa svojom aiohttp sesijom) + `close()` na svaki poziv. GCS je tu
    bio najmanje pogodjen (ADC token je process-keširан), ali reuse poravnava GCS
    sa ostalim backend-ima i uklanja per-call session setup. Vidi
    `resources/Nalazi i dnevnik.md` Nalaz #12.
    """

    def __init__(self, bucket_name: str, credentials_path: str | None = None):
        self._bucket_name = bucket_name
        self._credentials_path = credentials_path
        self._storage = None
        self._lock = asyncio.Lock()

    async def _get_storage(self):
        """Lazy-kreiraj i reuse-uj jedan Storage klijent."""
        if self._storage is None:
            async with self._lock:
                if self._storage is None:
                    from gcloud.aio.storage import Storage
                    if self._credentials_path:
                        self._storage = Storage(service_file=self._credentials_path)
                    else:
                        self._storage = Storage()
        return self._storage

    async def read(self, key: str) -> bytes:
        storage = await self._get_storage()
        try:
            return await storage.download(self._bucket_name, key)
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                raise KeyError(f"Key '{key}' not found in bucket '{self._bucket_name}'")
            raise

    async def write(self, key: str, data: bytes) -> None:
        storage = await self._get_storage()
        await storage.upload(self._bucket_name, key, data)

    async def close(self) -> None:
        if self._storage is not None:
            await self._storage.close()
            self._storage = None
