"""Compute endpoint for CPU-intensive benchmarking."""

from fastapi import APIRouter

from app.config import settings
from app.services.compute_service import compute_hash

router = APIRouter(tags=["benchmark"])


@router.get("/compute")
def compute() -> dict[str, str | int]:
    """
    CPU-intensive compute endpoint using iterative SHA-256 hashing.

    This is a synchronous endpoint as CPU-bound work doesn't benefit from async.

    Returns:
        dict: Hash result and number of iterations performed.
    """
    hash_result = compute_hash(settings.compute_iterations)

    return {
        "hash": hash_result,
        "iterations": settings.compute_iterations,
    }
