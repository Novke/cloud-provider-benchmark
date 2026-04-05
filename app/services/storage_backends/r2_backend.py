"""Cloudflare R2 storage backend (S3-compatible)."""

import aioboto3
from botocore.exceptions import ClientError

from .base import StorageBackend


class R2Backend(StorageBackend):
    """
    Cloudflare R2 storage backend.

    R2 is S3-compatible, so we use aioboto3 with a custom endpoint.
    Used as the "neutral" storage backend for fair cross-provider comparison.
    """

    def __init__(self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str):
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket_name = bucket_name
        self._session = aioboto3.Session()

    def _client_kwargs(self):
        return {
            "service_name": "s3",
            "endpoint_url": self._endpoint_url,
            "aws_access_key_id": self._access_key_id,
            "aws_secret_access_key": self._secret_access_key,
            "region_name": "auto",
        }

    async def read(self, key: str) -> bytes:
        """Read data from R2 bucket."""
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                response = await s3.get_object(Bucket=self._bucket_name, Key=key)
                return await response["Body"].read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise KeyError(f"Key '{key}' not found in R2 bucket '{self._bucket_name}'")
                raise

    async def write(self, key: str, data: bytes) -> None:
        """Write data to R2 bucket."""
        async with self._session.client(**self._client_kwargs()) as s3:
            await s3.put_object(Bucket=self._bucket_name, Key=key, Body=data)
