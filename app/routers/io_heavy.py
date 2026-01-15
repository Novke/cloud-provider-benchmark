"""I/O heavy endpoints for storage performance testing."""

import os
from fastapi import APIRouter

from app.config import settings
from app.services.storage_service import get_storage_backend

router = APIRouter(tags=["benchmark"], prefix="/io-heavy")


@router.get("/native")
async def io_heavy_native() -> dict[str, str | int]:
    """
    I/O heavy endpoint using cloud provider's native storage.

    This endpoint tests I/O performance using the provider's native storage
    service (e.g., S3 for AWS, Blob for Azure).

    Returns:
        dict: Operation details including bytes transferred and storage type.
    """
    backend = get_storage_backend(settings.storage_backend_native)

    # Generate 1KB of random data
    data = os.urandom(1024)
    key = "benchmark-test-native"

    # Write then read
    await backend.write(key, data)
    result = await backend.read(key)

    # Verify data integrity
    assert result == data, "Data integrity check failed"

    return {
        "operation": "read_write",
        "bytes": len(data),
        "storage": "native",
    }


@router.get("/neutral")
async def io_heavy_neutral() -> dict[str, str | int]:
    """
    I/O heavy endpoint using neutral storage (Cloudflare R2).

    This endpoint tests I/O performance using a neutral third-party storage
    service to provide a fair comparison across providers.

    Returns:
        dict: Operation details including bytes transferred and storage type.
    """
    backend = get_storage_backend(settings.storage_backend_neutral)

    # Generate 1KB of random data
    data = os.urandom(1024)
    key = "benchmark-test-neutral"

    # Write then read
    await backend.write(key, data)
    result = await backend.read(key)

    # Verify data integrity
    assert result == data, "Data integrity check failed"

    return {
        "operation": "read_write",
        "bytes": len(data),
        "storage": "neutral",
    }
