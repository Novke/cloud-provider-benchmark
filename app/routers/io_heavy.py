"""I/O heavy endpoints for storage performance testing."""

import os
import time

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.storage_service import get_storage_backend

router = APIRouter(tags=["benchmark"], prefix="/io-heavy")


async def _run_io_benchmark(backend_type: str, storage_label: str) -> dict:
    """Run write/read benchmark and return timing metrics."""
    backend = get_storage_backend(backend_type)
    data = os.urandom(1024)
    key = f"benchmark-test-{storage_label}"

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
async def io_heavy_native() -> dict:
    """I/O heavy endpoint using cloud provider's native storage."""
    return await _run_io_benchmark(settings.storage_backend_native, "native")


@router.get("/neutral")
async def io_heavy_neutral() -> dict:
    """I/O heavy endpoint using neutral storage (Cloudflare R2)."""
    return await _run_io_benchmark(settings.storage_backend_neutral, "neutral")
