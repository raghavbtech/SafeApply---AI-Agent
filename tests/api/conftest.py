"""Pytest fixtures for FastAPI TestClient and AsyncClient."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.schemas.auth import UserPrincipal
from backend.security.identity import create_access_token


@pytest.fixture
def demo_principal() -> UserPrincipal:
    return UserPrincipal(
        user_id="test_candidate@safeapply.local",
        email="test_candidate@safeapply.local",
        full_name="Test Candidate",
        role="candidate",
    )


@pytest.fixture
def auth_headers(demo_principal: UserPrincipal) -> dict:
    token = create_access_token(demo_principal)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
