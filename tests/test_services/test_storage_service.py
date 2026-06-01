"""Tests for storage service."""

import pytest

from app.services.storage_backends import MockStorageBackend
from app.services.storage_service import get_storage_backend


@pytest.mark.asyncio
async def test_mock_storage_write_and_read() -> None:
    """Test that MockStorageBackend can write and read data."""
    storage = MockStorageBackend()
    test_key = "test-key"
    test_data = b"test data content"

    await storage.write(test_key, test_data)
    result = await storage.read(test_key)

    assert result == test_data


@pytest.mark.asyncio
async def test_mock_storage_read_nonexistent_key() -> None:
    """Test that reading non-existent key raises KeyError."""
    storage = MockStorageBackend()

    with pytest.raises(KeyError) as exc_info:
        await storage.read("nonexistent-key")

    assert "nonexistent-key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mock_storage_overwrite() -> None:
    """Test that writing to same key overwrites data."""
    storage = MockStorageBackend()
    test_key = "test-key"

    await storage.write(test_key, b"first data")
    await storage.write(test_key, b"second data")

    result = await storage.read(test_key)
    assert result == b"second data"


@pytest.mark.asyncio
async def test_mock_storage_multiple_keys() -> None:
    """Test that MockStorageBackend can handle multiple keys."""
    storage = MockStorageBackend()

    await storage.write("key1", b"data1")
    await storage.write("key2", b"data2")
    await storage.write("key3", b"data3")

    assert await storage.read("key1") == b"data1"
    assert await storage.read("key2") == b"data2"
    assert await storage.read("key3") == b"data3"


def test_get_storage_backend_mock() -> None:
    """Test that factory returns MockStorageBackend for 'mock' type."""
    backend = get_storage_backend("mock")
    assert isinstance(backend, MockStorageBackend)


def test_get_storage_backend_invalid_type() -> None:
    """Test that factory raises ValueError for invalid backend type."""
    with pytest.raises(ValueError) as exc_info:
        get_storage_backend("invalid-type")

    assert "Unsupported storage backend type" in str(exc_info.value)
    assert "invalid-type" in str(exc_info.value)


def test_get_storage_backend_returns_cached_instance() -> None:
    """Factory kešira backend po tipu i reuse-uje isti instance.

    Reuse je namerni dizajn (Nalaz #12): instanca se reuse-uje da bi se SDK klijent
    (connection pool / credential) reuse-ovao umesto da se pravi po pozivu. Cache se
    resetuje izmedju testova preko cleanup_mock_storage fixture-a.
    """
    backend1 = get_storage_backend("mock")
    backend2 = get_storage_backend("mock")

    assert backend1 is backend2
