"""Compute endpoint for CPU-intensive benchmarking."""

import time
from typing import Optional

from fastapi import APIRouter, Query

from app.config import settings
from app.services.compute_service import compute_hash

router = APIRouter(tags=["benchmark"])


@router.get("/compute")
def compute(
    iterations: Optional[int] = Query(
        default=None,
        ge=1,
        description="Number of SHA-256 iterations. Uses COMPUTE_ITERATIONS from env if not provided."
    )
) -> dict[str, str | int]:
    """
    CPU-intensive compute endpoint using iterative SHA-256 hashing.

    This is a synchronous endpoint as CPU-bound work doesn't benefit from async.

    Args:
        iterations: Optional number of iterations. If not provided, uses config value.

    Returns:
        dict: Hash result and number of iterations performed.
    """
    iteration_count = iterations if iterations is not None else settings.compute_iterations

    start_time = time.time()
    hash_result = compute_hash(iteration_count)
    elapsed_time = time.time() - start_time

    print(f"Compute completed: iterations={iteration_count}, time={elapsed_time:.4f}s")

    return {
        "hash": hash_result,
        "iterations": iteration_count,
    }
