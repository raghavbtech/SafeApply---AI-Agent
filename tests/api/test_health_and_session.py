"""Tests for health and anonymous session endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient):
    resp = await async_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready(async_client: AsyncClient):
    resp = await async_client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "storage_backend" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_first_visit_auto_session(async_client: AsyncClient):
    # First request with no cookie
    resp = await async_client.get("/api/v1/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["session_id"].startswith("anon_")
    assert data["has_profile"] is False
    assert data["has_resume"] is False

    # Check Set-Cookie header is issued
    assert "set-cookie" in resp.headers
    cookie_str = resp.headers["set-cookie"]
    assert "safeapply_session=" in cookie_str


@pytest.mark.asyncio
async def test_returning_visitor_retains_session(async_client: AsyncClient):
    # Initial request
    resp1 = await async_client.get("/api/v1/session")
    sess1_id = resp1.json()["session_id"]
    cookie_val = resp1.cookies.get("safeapply_session")

    # Second request passing the cookie
    resp2 = await async_client.get("/api/v1/session", cookies={"safeapply_session": cookie_val})
    assert resp2.status_code == 200
    sess2_id = resp2.json()["session_id"]
    assert sess1_id == sess2_id


@pytest.mark.asyncio
async def test_session_purge_data(async_client: AsyncClient):
    # Get session
    resp1 = await async_client.get("/api/v1/session")
    cookie_val = resp1.cookies.get("safeapply_session")

    # Call purge
    resp_purge = await async_client.delete(
        "/api/v1/session/data",
        cookies={"safeapply_session": cookie_val},
    )
    assert resp_purge.status_code == 200
    assert resp_purge.json()["success"] is True
