"""Tests for quick endpoint."""

import pytest
from httpx import AsyncClient
import time


@pytest.mark.asyncio
async def test_quick_returns_200(client: AsyncClient) -> None:
    """Test that quick endpoint returns 200 status code."""
    response = await client.get("/quick")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_quick_response_body(client: AsyncClient) -> None:
    """Test that quick endpoint returns correct response structure."""
    response = await client.get("/quick")
    data = response.json()
    assert data == {"message": "ok", "hold_ms": 0}


@pytest.mark.asyncio
async def test_quick_response_time(client: AsyncClient) -> None:
    """Test that quick endpoint responds quickly (< 100ms)."""
    start = time.time()
    response = await client.get("/quick")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    assert response.status_code == 200
    assert elapsed < 100  # Should be fast


@pytest.mark.asyncio
async def test_quick_with_hold_100ms(client: AsyncClient) -> None:
    """Test that quick endpoint with hold=100 waits approximately 100ms."""
    start = time.time()
    response = await client.get("/quick?hold=100")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "ok", "hold_ms": 100}
    # Allow some variance in timing (99-150ms)
    assert 99 <= elapsed <= 150


@pytest.mark.asyncio
async def test_quick_with_hold_zero(client: AsyncClient) -> None:
    """Test that quick endpoint with hold=0 is fast."""
    start = time.time()
    response = await client.get("/quick?hold=0")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    assert response.status_code == 200
    data = response.json()
    assert data == {"message": "ok", "hold_ms": 0}
    assert elapsed < 100


@pytest.mark.asyncio
async def test_quick_with_invalid_hold_negative(client: AsyncClient) -> None:
    """Test that quick endpoint rejects negative hold values."""
    response = await client.get("/quick?hold=-100")
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_quick_with_invalid_hold_too_large(client: AsyncClient) -> None:
    """Test that quick endpoint rejects hold values > 10000."""
    response = await client.get("/quick?hold=10001")
    assert response.status_code == 422  # Validation error
