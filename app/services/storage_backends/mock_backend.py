"""Mock storage backend for testing and development."""

from typing import Dict, ClassVar

from .base import StorageBackend


class MockStorageBackend(StorageBackend):
    """
    In-memory mock storage backend for testing.

    Uses class-level storage (singleton pattern) so all instances
    share the same data. This allows tests to verify data integrity
    across different backend instances.
    """

    # Class-level storage shared by all instances (singleton-like)
    _shared_storage: ClassVar[Dict[str, bytes]] = {}

    def __init__(self):
        """Initialize mock storage (uses shared class-level storage)."""
        # Instance uses class-level storage
        pass

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
        if key not in MockStorageBackend._shared_storage:
            raise KeyError(f"Key '{key}' not found in storage")
        return MockStorageBackend._shared_storage[key]

    async def write(self, key: str, data: bytes) -> None:
        """
        Write data to mock storage.

        Args:
            key: Storage key.
            data: Data to write.
        """
        MockStorageBackend._shared_storage[key] = data

    @classmethod
    def clear(cls) -> None:
        """Clear all data from shared storage (useful for tests)."""
        cls._shared_storage.clear()
