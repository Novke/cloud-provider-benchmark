"""Quick endpoint for baseline latency and throughput testing."""

from fastapi import APIRouter

router = APIRouter(tags=["benchmark"])


@router.get("/quick")
async def quick() -> dict[str, str | int]:
    """
    Quick endpoint for baseline latency testing.

    Returns:
        dict: Message and hold time in milliseconds.
    """
    return {"message": "ok", "hold_ms": 0}
