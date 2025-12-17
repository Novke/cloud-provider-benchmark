"""Tests for health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Test that health endpoint returns 200 status code."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_body(client: AsyncClient) -> None:
    """Test that health endpoint returns correct response body."""
    response = await client.get("/health")
    assert response.json() == {"status": "healthy"}
