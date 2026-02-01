"""Integration tests for the complete benchmark application."""

import asyncio
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_all_endpoints_return_200(client: AsyncClient) -> None:
    """Test that all benchmark endpoints return 200 status code."""
    endpoints = [
        "/health",
        "/quick",
        "/compute",
        "/io-heavy/native",
        "/io-heavy/neutral",
    ]

    for endpoint in endpoints:
        response = await client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} returned {response.status_code}"


@pytest.mark.asyncio
async def test_all_endpoints_return_json(client: AsyncClient) -> None:
    """Test that all endpoints return valid JSON responses."""
    endpoints = [
        "/health",
        "/quick",
        "/compute",
        "/io-heavy/native",
        "/io-heavy/neutral",
    ]

    for endpoint in endpoints:
        response = await client.get(endpoint)
        data = response.json()
        assert isinstance(data, dict), f"{endpoint} did not return a dict"


@pytest.mark.asyncio
async def test_full_benchmark_sequence(client: AsyncClient) -> None:
    """Test a complete benchmark sequence as a real benchmark run would execute."""
    # 1. Health check first
    health = await client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"

    # 2. Quick baseline (no hold)
    quick = await client.get("/quick")
    assert quick.status_code == 200
    assert quick.json()["message"] == "ok"

    # 3. Compute workload
    compute = await client.get("/compute?iterations=1000")
    assert compute.status_code == 200
    compute_data = compute.json()
    assert "hash" in compute_data
    assert len(compute_data["hash"]) == 64

    # 4. I/O operations
    io_native = await client.get("/io-heavy/native")
    assert io_native.status_code == 200
    assert io_native.json()["bytes"] == 1024

    io_neutral = await client.get("/io-heavy/neutral")
    assert io_neutral.status_code == 200
    assert io_neutral.json()["bytes"] == 1024


@pytest.mark.asyncio
async def test_concurrent_quick_requests(client: AsyncClient) -> None:
    """Test that multiple concurrent /quick requests work correctly."""
    async def make_request():
        response = await client.get("/quick")
        return response.status_code

    # Run 10 concurrent requests
    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)

    assert all(status == 200 for status in results)


@pytest.mark.asyncio
async def test_concurrent_io_heavy_requests(client: AsyncClient) -> None:
    """Test that multiple concurrent /io-heavy requests work correctly."""
    async def make_native_request():
        response = await client.get("/io-heavy/native")
        return response.status_code, response.json()

    async def make_neutral_request():
        response = await client.get("/io-heavy/neutral")
        return response.status_code, response.json()

    # Run 5 native and 5 neutral concurrently
    tasks = [make_native_request() for _ in range(5)]
    tasks += [make_neutral_request() for _ in range(5)]
    results = await asyncio.gather(*tasks)

    for status, data in results:
        assert status == 200
        assert data["bytes"] == 1024


@pytest.mark.asyncio
async def test_quick_with_hold_concurrent(client: AsyncClient) -> None:
    """Test concurrent /quick requests with hold parameter."""
    async def make_request(hold_ms: int):
        response = await client.get(f"/quick?hold={hold_ms}")
        return response.status_code, response.json()["hold_ms"]

    # Different hold values concurrently
    tasks = [
        make_request(50),
        make_request(100),
        make_request(50),
    ]
    results = await asyncio.gather(*tasks)

    assert results[0] == (200, 50)
    assert results[1] == (200, 100)
    assert results[2] == (200, 50)


@pytest.mark.asyncio
async def test_compute_deterministic_across_calls(client: AsyncClient) -> None:
    """Test that /compute returns same hash for same iterations."""
    response1 = await client.get("/compute?iterations=100")
    response2 = await client.get("/compute?iterations=100")

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["hash"] == response2.json()["hash"]


@pytest.mark.asyncio
async def test_io_heavy_isolation_between_types(client: AsyncClient) -> None:
    """Test that native and neutral storage operations are isolated."""
    # Call native
    native_response = await client.get("/io-heavy/native")
    assert native_response.status_code == 200
    assert native_response.json()["storage"] == "native"

    # Call neutral
    neutral_response = await client.get("/io-heavy/neutral")
    assert neutral_response.status_code == 200
    assert neutral_response.json()["storage"] == "neutral"

    # Verify different storage identifiers
    assert native_response.json()["storage"] != neutral_response.json()["storage"]


@pytest.mark.asyncio
async def test_repeated_endpoint_calls_stability(client: AsyncClient) -> None:
    """Test that endpoints remain stable across repeated calls."""
    for _ in range(5):
        health = await client.get("/health")
        quick = await client.get("/quick")
        compute = await client.get("/compute?iterations=100")
        io_native = await client.get("/io-heavy/native")

        assert health.status_code == 200
        assert quick.status_code == 200
        assert compute.status_code == 200
        assert io_native.status_code == 200
