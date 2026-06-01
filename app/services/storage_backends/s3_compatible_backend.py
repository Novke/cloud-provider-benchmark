"""S3-compatible storage backend (AWS S3, Cloudflare R2, Hetzner Object Storage)."""

import asyncio

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .base import StorageBackend

# Connection pool velicina za reused klijent. Botocore default je 10 — premalo za
# concurrent benchmark load (50 VU), gde bi 40 zahteva cekalo na konekciju. 64
# pokriva io profil (max 50 VU) i poravnava S3 sa aiohttp default-om (~100) koji
# koriste Azure/GCS aio klijenti.
_MAX_POOL_CONNECTIONS = 64


class S3CompatibleBackend(StorageBackend):
    """
    Generic S3-compatible storage backend.

    Works with any S3-compatible service: AWS S3, Cloudflare R2,
    Hetzner Object Storage, MinIO, etc. Each service just needs
    different credentials and endpoint configuration.

    Klijent se kreira JEDNOM (lazy, prvi poziv) i reuse-uje kroz sve read/write
    pozive. Raniji kod je pravio nov klijent (nov connection pool + TLS handshake)
    na svaki poziv; pod konkurentnoscu je to dominiralo merenje (pool exhaustion +
    errori) i merilo SDK client-init, ne storage performanse. Vidi
    `resources/Nalazi i dnevnik.md` Nalaz #12.
    """

    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        region_name: str = "auto",
        endpoint_url: str | None = None,
    ):
        self._bucket_name = bucket_name
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region_name = region_name
        self._endpoint_url = endpoint_url
        self._session = aioboto3.Session()
        self._client = None
        self._client_cm = None
        self._lock = asyncio.Lock()

    def _client_kwargs(self) -> dict:
        kwargs = {
            "service_name": "s3",
            "region_name": self._region_name,
            "config": Config(max_pool_connections=_MAX_POOL_CONNECTIONS),
        }
        if self._access_key_id and self._secret_access_key:
            kwargs["aws_access_key_id"] = self._access_key_id
            kwargs["aws_secret_access_key"] = self._secret_access_key
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def _get_client(self):
        """Lazy-kreiraj i reuse-uj jedan aioboto3 klijent (thread/task-safe)."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    self._client_cm = self._session.client(**self._client_kwargs())
                    self._client = await self._client_cm.__aenter__()
        return self._client

    async def read(self, key: str) -> bytes:
        s3 = await self._get_client()
        try:
            response = await s3.get_object(Bucket=self._bucket_name, Key=key)
            return await response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise KeyError(f"Key '{key}' not found in bucket '{self._bucket_name}'")
            raise

    async def write(self, key: str, data: bytes) -> None:
        s3 = await self._get_client()
        await s3.put_object(Bucket=self._bucket_name, Key=key, Body=data)

    async def close(self) -> None:
        if self._client_cm is not None:
            await self._client_cm.__aexit__(None, None, None)
            self._client = None
            self._client_cm = None
