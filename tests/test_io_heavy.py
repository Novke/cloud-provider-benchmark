"""Tests for I/O heavy endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_io_heavy_native_returns_200(client: AsyncClient) -> None:
    """Test that /io-heavy/native endpoint returns 200 status code."""
    response = await client.get("/io-heavy/native")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_io_heavy_native_response_structure(client: AsyncClient) -> None:
    """Test that /io-heavy/native returns correct response structure."""
    response = await client.get("/io-heavy/native")
    data = response.json()

    assert "operation" in data
    assert "bytes" in data
    assert "storage" in data
    assert data["operation"] == "read_write"
    assert data["bytes"] == 1024
    assert data["storage"] == "native"


@pytest.mark.asyncio
async def test_io_heavy_neutral_returns_200(client: AsyncClient) -> None:
    """Test that /io-heavy/neutral endpoint returns 200 status code."""
    response = await client.get("/io-heavy/neutral")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_io_heavy_neutral_response_structure(client: AsyncClient) -> None:
    """Test that /io-heavy/neutral returns correct response structure."""
    response = await client.get("/io-heavy/neutral")
    data = response.json()

    assert "operation" in data
    assert "bytes" in data
    assert "storage" in data
    assert data["operation"] == "read_write"
    assert data["bytes"] == 1024
    assert data["storage"] == "neutral"


@pytest.mark.asyncio
async def test_io_heavy_native_multiple_calls(client: AsyncClient) -> None:
    """Test that /io-heavy/native can be called multiple times."""
    response1 = await client.get("/io-heavy/native")
    response2 = await client.get("/io-heavy/native")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Both should have same structure
    assert data1["storage"] == data2["storage"] == "native"
    assert data1["bytes"] == data2["bytes"] == 1024


@pytest.mark.asyncio
async def test_io_heavy_neutral_multiple_calls(client: AsyncClient) -> None:
    """Test that /io-heavy/neutral can be called multiple times."""
    response1 = await client.get("/io-heavy/neutral")
    response2 = await client.get("/io-heavy/neutral")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Both should have same structure
    assert data1["storage"] == data2["storage"] == "neutral"
    assert data1["bytes"] == data2["bytes"] == 1024


@pytest.mark.asyncio
async def test_io_heavy_endpoints_use_different_storage(client: AsyncClient) -> None:
    """Test that native and neutral endpoints report different storage types."""
    response_native = await client.get("/io-heavy/native")
    response_neutral = await client.get("/io-heavy/neutral")

    data_native = response_native.json()
    data_neutral = response_neutral.json()

    assert data_native["storage"] == "native"
    assert data_neutral["storage"] == "neutral"
    assert data_native["storage"] != data_neutral["storage"]
