import os
os.environ["SAFEAPPLY_ENV"] = "testing"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from backend.config import settings
settings.environment = "testing"
settings.safeapply_user_id = ""
from backend.main import app
from backend.schemas.auth import SessionPrincipal
from backend.security.session import SessionStore


@pytest.fixture
def demo_session() -> tuple[SessionPrincipal, str]:
    principal, raw_token = SessionStore.create_session(user_agent="pytest-client")
    return principal, raw_token


@pytest.fixture
def demo_principal(demo_session: tuple[SessionPrincipal, str]) -> SessionPrincipal:
    return demo_session[0]


@pytest.fixture
def auth_headers(demo_session: tuple[SessionPrincipal, str]) -> dict:
    raw_token = demo_session[1]
    return {"Authorization": f"Bearer {raw_token}"}


@pytest.fixture
def session_cookies(demo_session: tuple[SessionPrincipal, str]) -> dict:
    raw_token = demo_session[1]
    return {"safeapply_session": raw_token}


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
