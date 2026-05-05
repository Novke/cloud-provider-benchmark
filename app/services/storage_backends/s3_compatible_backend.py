"""S3-compatible storage backend (AWS S3, Cloudflare R2, Hetzner Object Storage)."""

import aioboto3
from botocore.exceptions import ClientError

from .base import StorageBackend


class S3CompatibleBackend(StorageBackend):
    """
    Generic S3-compatible storage backend.

    Works with any S3-compatible service: AWS S3, Cloudflare R2,
    Hetzner Object Storage, MinIO, etc. Each service just needs
    different credentials and endpoint configuration.
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

    def _client_kwargs(self) -> dict:
        kwargs = {
            "service_name": "s3",
            "region_name": self._region_name,
        }
        if self._access_key_id and self._secret_access_key:
            kwargs["aws_access_key_id"] = self._access_key_id
            kwargs["aws_secret_access_key"] = self._secret_access_key
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    async def read(self, key: str) -> bytes:
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                response = await s3.get_object(Bucket=self._bucket_name, Key=key)
                return await response["Body"].read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise KeyError(f"Key '{key}' not found in bucket '{self._bucket_name}'")
                raise

    async def write(self, key: str, data: bytes) -> None:
        async with self._session.client(**self._client_kwargs()) as s3:
            await s3.put_object(Bucket=self._bucket_name, Key=key, Body=data)
