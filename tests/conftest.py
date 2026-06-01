"""Pytest fixtures and configuration."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.storage_backends import MockStorageBackend
from app.services.storage_service import reset_storage_backend_cache


@pytest_asyncio.fixture
async def client():
    """
    Create an async test client for the FastAPI application.

    Yields:
        AsyncClient: Async HTTP client for testing.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def cleanup_mock_storage():
    """
    Automatically clear MockStorageBackend shared storage after each test.

    This fixture runs automatically (autouse=True) for every test,
    ensuring test isolation by cleaning up any data written to
    the mock storage backend.
    """
    # Setup: nothing needed before test
    yield
    # Teardown: clear storage + izbaci keširane backend instance (izolacija)
    MockStorageBackend.clear()
    reset_storage_backend_cache()
