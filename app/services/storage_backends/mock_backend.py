"""Mock storage backend for testing and development."""

from typing import Dict

from .base import StorageBackend


class MockStorageBackend(StorageBackend):
    """In-memory mock storage backend for testing."""

    def __init__(self):
        """Initialize mock storage with empty dictionary."""
        self._storage: Dict[str, bytes] = {}

    async def read(self, key: str) -> bytes:
        """
        Read data from mock storage.

        Args:
            key: Storage key.

        Returns:
            bytes: Data from storage.

        Raises:
            KeyError: If key does not exist.
        """
        if key not in self._storage:
            raise KeyError(f"Key '{key}' not found in storage")
        return self._storage[key]

    async def write(self, key: str, data: bytes) -> None:
        """
        Write data to mock storage.

        Args:
            key: Storage key.
            data: Data to write.
        """
        self._storage[key] = data
