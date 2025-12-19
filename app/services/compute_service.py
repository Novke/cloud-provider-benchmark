"""Compute service for CPU-intensive hash computation."""

import hashlib


def compute_hash(iterations: int) -> str:
    """
    Perform CPU-intensive computation using iterative SHA-256 hashing.

    Args:
        iterations: Number of times to apply SHA-256 hash.

    Returns:
        str: Final hash as hexadecimal string (64 characters).
    """
    data = b"cloud-benchmark-payload"

    for _ in range(iterations):
        hash_obj = hashlib.sha256(data)
        data = hash_obj.digest()

    return data.hex()
