"""I/O heavy endpoints for storage performance testing."""

import os
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.services.storage_service import get_storage_backend

router = APIRouter(tags=["benchmark"], prefix="/io-heavy")

# 100MB max to prevent abuse
MAX_BYTES = 100 * 1024 * 1024


async def _run_io_benchmark(backend_type: str, storage_label: str, size_bytes: int) -> dict:
    """Run write/read benchmark and return timing metrics."""
    backend = get_storage_backend(backend_type)
    data = os.urandom(size_bytes)
    key = f"benchmark-{storage_label}-{uuid.uuid4().hex[:8]}"

    t0 = time.time()
    await backend.write(key, data)
    write_ms = (time.time() - t0) * 1000

    t1 = time.time()
    result = await backend.read(key)
    read_ms = (time.time() - t1) * 1000

    if result != data:
        raise HTTPException(status_code=500, detail="Data integrity check failed")

    return {
        "operation": "read_write",
        "bytes": len(data),
        "storage": storage_label,
        "write_ms": round(write_ms, 2),
        "read_ms": round(read_ms, 2),
        "total_ms": round(write_ms + read_ms, 2),
    }


@router.get("/native")
async def io_heavy_native(
    bytes: Optional[int] = Query(default=1024, ge=1, le=MAX_BYTES, description="Payload size in bytes")
) -> dict:
    """I/O heavy endpoint using cloud provider's native storage."""
    return await _run_io_benchmark(settings.storage_backend_native, "native", bytes)


@router.get("/neutral")
async def io_heavy_neutral(
    bytes: Optional[int] = Query(default=1024, ge=1, le=MAX_BYTES, description="Payload size in bytes")
) -> dict:
    """I/O heavy endpoint using neutral storage (Cloudflare R2)."""
    return await _run_io_benchmark(settings.storage_backend_neutral, "neutral", bytes)
