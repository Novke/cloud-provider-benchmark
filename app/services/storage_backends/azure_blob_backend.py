"""Azure Blob Storage backend."""

from .base import StorageBackend


class AzureBlobBackend(StorageBackend):
    """
    Azure Blob Storage backend using azure-storage-blob async API.

    Two auth modes:
    - account_url + DefaultAzureCredential (preferred when running on Azure VM with managed identity)
    - connection_string (embedded account key, for testing or non-Azure compute)
    """

    def __init__(
        self,
        container_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ):
        self._container_name = container_name
        self._connection_string = connection_string
        self._account_url = account_url

    def _get_client(self):
        from azure.storage.blob.aio import BlobServiceClient
        if self._connection_string:
            return BlobServiceClient.from_connection_string(self._connection_string)
        if self._account_url:
            from azure.identity.aio import DefaultAzureCredential
            return BlobServiceClient(self._account_url, credential=DefaultAzureCredential())
        raise ValueError("AzureBlobBackend requires either connection_string or account_url")

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
