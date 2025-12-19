"""Quick endpoint for baseline latency and throughput testing."""

import asyncio
from fastapi import APIRouter, Query

router = APIRouter(tags=["benchmark"])


@router.get("/quick")
async def quick(
    hold: int = Query(default=0, ge=0, le=10000, description="Hold time in milliseconds (0-10000)")
) -> dict[str, str | int]:
    """
    Quick endpoint for baseline latency and concurrency testing.

    Args:
        hold: Optional hold time in milliseconds (0-10000). Default is 0.

    Returns:
        dict: Message and hold time in milliseconds.
    """
    if hold > 0:
        await asyncio.sleep(hold / 1000)

    return {"message": "ok", "hold_ms": hold}
