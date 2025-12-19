"""Tests for compute endpoint."""

import pytest
from httpx import AsyncClient

from app.config import settings


@pytest.mark.asyncio
async def test_compute_returns_200(client: AsyncClient) -> None:
    """Test that compute endpoint returns 200 status code."""
    response = await client.get("/compute")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_compute_response_structure(client: AsyncClient) -> None:
    """Test that compute endpoint returns correct response structure."""
    response = await client.get("/compute")
    data = response.json()

    assert "hash" in data
    assert "iterations" in data
    assert isinstance(data["hash"], str)
    assert isinstance(data["iterations"], int)


@pytest.mark.asyncio
async def test_compute_hash_is_valid_hex(client: AsyncClient) -> None:
    """Test that compute endpoint returns valid hex string."""
    response = await client.get("/compute")
    data = response.json()

    hash_value = data["hash"]
    assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
    # Verify it's valid hex
    int(hash_value, 16)


@pytest.mark.asyncio
async def test_compute_iterations_matches_config(client: AsyncClient) -> None:
    """Test that compute endpoint uses configured iterations."""
    response = await client.get("/compute")
    data = response.json()

    assert data["iterations"] == settings.compute_iterations


@pytest.mark.asyncio
async def test_compute_returns_consistent_hash(client: AsyncClient) -> None:
    """Test that compute endpoint returns consistent hash for same iterations."""
    response1 = await client.get("/compute")
    response2 = await client.get("/compute")

    data1 = response1.json()
    data2 = response2.json()

    # Same iterations should produce same hash
    assert data1["hash"] == data2["hash"]
    assert data1["iterations"] == data2["iterations"]
