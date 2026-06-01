"""Azure Blob Storage backend."""

import asyncio

from .base import StorageBackend


class AzureBlobBackend(StorageBackend):
    """
    Azure Blob Storage backend using azure-storage-blob async API.

    Two auth modes:
    - account_url + DefaultAzureCredential (preferred when running on Azure VM with managed identity)
    - connection_string (embedded account key, for testing or non-Azure compute)

    Service klijent I credential se kreiraju JEDNOM (lazy) i reuse-uju. Raniji kod
    je pravio nov `BlobServiceClient` + nov `DefaultAzureCredential` na svaki poziv
    — sto je znacilo nov managed-identity IMDS token fetch po requestu. Pod
    konkurentnoscu je IMDS throttle dizao write latenciju na ~11s (merilo token
    fetch, ne Blob storage). Vidi `resources/Nalazi i dnevnik.md` Nalaz #12.
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
        self._service = None
        self._credential = None
        self._lock = asyncio.Lock()

    async def _get_service(self):
        """Lazy-kreiraj i reuse-uj jedan BlobServiceClient (+ credential)."""
        if self._service is None:
            async with self._lock:
                if self._service is None:
                    from azure.storage.blob.aio import BlobServiceClient
                    if self._connection_string:
                        self._service = BlobServiceClient.from_connection_string(
                            self._connection_string
                        )
                    elif self._account_url:
                        from azure.identity.aio import DefaultAzureCredential
                        self._credential = DefaultAzureCredential()
                        self._service = BlobServiceClient(
                            self._account_url, credential=self._credential
                        )
                    else:
                        raise ValueError(
                            "AzureBlobBackend requires either connection_string or account_url"
                        )
        return self._service

    async def read(self, key: str) -> bytes:
        service = await self._get_service()
        blob = service.get_blob_client(container=self._container_name, blob=key)
        try:
            download = await blob.download_blob()
            return await download.readall()
        except Exception as e:
            if "BlobNotFound" in str(e):
                raise KeyError(f"Key '{key}' not found in container '{self._container_name}'")
            raise

    async def write(self, key: str, data: bytes) -> None:
        service = await self._get_service()
        blob = service.get_blob_client(container=self._container_name, blob=key)
        await blob.upload_blob(data, overwrite=True)

    async def close(self) -> None:
        if self._service is not None:
            await self._service.close()
            self._service = None
        if self._credential is not None:
            await self._credential.close()
            self._credential = None
