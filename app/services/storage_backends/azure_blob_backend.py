"""Azure Blob Storage backend."""

from .base import StorageBackend


class AzureBlobBackend(StorageBackend):
    """
    Azure Blob Storage backend using azure-storage-blob async API.

    Used as native storage backend when running on Azure (VM, ACI, Functions).
    """

    def __init__(self, connection_string: str, container_name: str):
        self._connection_string = connection_string
        self._container_name = container_name

    def _get_client(self):
        from azure.storage.blob.aio import BlobServiceClient
        return BlobServiceClient.from_connection_string(self._connection_string)

    async def read(self, key: str) -> bytes:
        async with self._get_client() as service:
            blob = service.get_blob_client(
                container=self._container_name, blob=key
            )
            try:
                download = await blob.download_blob()
                return await download.readall()
            except Exception as e:
                if "BlobNotFound" in str(e):
                    raise KeyError(f"Key '{key}' not found in container '{self._container_name}'")
                raise

    async def write(self, key: str, data: bytes) -> None:
        async with self._get_client() as service:
            blob = service.get_blob_client(
                container=self._container_name, blob=key
            )
            await blob.upload_blob(data, overwrite=True)
