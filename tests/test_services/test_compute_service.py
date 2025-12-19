"""Tests for compute service."""

import time
from app.services.compute_service import compute_hash


def test_compute_hash_returns_consistent_results() -> None:
    """Test that compute_hash returns same output for same input."""
    result1 = compute_hash(100)
    result2 = compute_hash(100)
    assert result1 == result2


def test_compute_hash_returns_valid_hex_string() -> None:
    """Test that compute_hash returns valid 64-character hex string."""
    result = compute_hash(100)
    assert isinstance(result, str)
    assert len(result) == 64
    # Verify it's valid hex
    int(result, 16)


def test_compute_hash_completes_with_1000_iterations() -> None:
    """Test that compute_hash completes successfully with 1000 iterations."""
    result = compute_hash(1000)
    assert isinstance(result, str)
    assert len(result) == 64


def test_compute_hash_higher_iterations_take_longer() -> None:
    """Test that higher iterations take more time (basic performance sanity check)."""
    start = time.time()
    compute_hash(100)
    time_100 = time.time() - start

    start = time.time()
    compute_hash(10000)
    time_10000 = time.time() - start

    # 10000 iterations should take noticeably longer than 100
    assert time_10000 > time_100


def test_compute_hash_different_iterations_different_results() -> None:
    """Test that different iteration counts produce different hashes."""
    result1 = compute_hash(100)
    result2 = compute_hash(200)
    assert result1 != result2
