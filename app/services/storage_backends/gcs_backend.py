"""Google Cloud Storage backend."""

from .base import StorageBackend


class GCSBackend(StorageBackend):
    """
    Google Cloud Storage backend using gcloud-aio-storage.

    Used as native storage backend when running on GCP (GCE, Cloud Run, Cloud Functions).
    Uses Application Default Credentials (ADC) when credentials_path is not provided,
    which works automatically on GCP compute environments.
    """

    def __init__(self, bucket_name: str, credentials_path: str | None = None):
        self._bucket_name = bucket_name
        self._credentials_path = credentials_path

    def _get_storage(self):
        from gcloud.aio.storage import Storage
        if self._credentials_path:
            return Storage(service_file=self._credentials_path)
        return Storage()

    async def read(self, key: str) -> bytes:
        storage = self._get_storage()
        try:
            return await storage.download(self._bucket_name, key)
        except Exception as e:
            if "404" in str(e) or "Not Found" in str(e):
                raise KeyError(f"Key '{key}' not found in bucket '{self._bucket_name}'")
            raise
        finally:
            await storage.close()

    async def write(self, key: str, data: bytes) -> None:
        storage = self._get_storage()
        try:
            await storage.upload(self._bucket_name, key, data)
        finally:
            await storage.close()
