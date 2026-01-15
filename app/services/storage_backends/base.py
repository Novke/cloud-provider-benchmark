"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """
        Read data from storage.

        Args:
            key: Storage key/path.

        Returns:
            bytes: Data retrieved from storage.

        Raises:
            KeyError: If key does not exist.
        """
        pass

    @abstractmethod
    async def write(self, key: str, data: bytes) -> None:
        """
        Write data to storage.

        Args:
            key: Storage key/path.
            data: Data to write.
        """
        pass
