"""Cloudflare R2 storage backend (S3-compatible).

Thin wrapper around S3CompatibleBackend for backwards compatibility.
R2 is the "neutral" storage backend for fair cross-provider comparison.
"""

from .s3_compatible_backend import S3CompatibleBackend


class R2Backend(S3CompatibleBackend):
    """Cloudflare R2 storage backend."""

    def __init__(self, endpoint_url: str, access_key_id: str, secret_access_key: str, bucket_name: str):
        super().__init__(
            bucket_name=bucket_name,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region_name="auto",
            endpoint_url=endpoint_url,
        )
