"""Health check endpoint with cold start detection."""

import time

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict:
    """
    Health check endpoint with cold start detection.

    Returns:
        dict: Status, cold start flag, and uptime information.
    """
    now = time.time()
    start_time = request.app.state.start_time
    is_cold = not request.app.state.first_request_received
    request.app.state.first_request_received = True

    return {
        "status": "healthy",
        "cold_start": is_cold,
        "uptime_seconds": round(now - start_time, 2),
    }
