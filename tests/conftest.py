"""Pytest fixtures and configuration."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


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
