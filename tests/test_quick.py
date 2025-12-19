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
