"""Tests for candidate profile, resume upload, and IDOR cross-user rejection."""

import pytest
from httpx import AsyncClient
from backend.security.identity import create_access_token
from backend.schemas.auth import UserPrincipal


@pytest.mark.asyncio
async def test_profile_crud_and_resume(async_client: AsyncClient, auth_headers: dict):
    # 1. Get profile
    resp = await async_client.get("/api/v1/profile", headers=auth_headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert "skills" in profile
    assert "full_name" in profile

    # 2. Update profile
    updated = dict(profile)
    updated["full_name"] = "Verified Candidate"
    updated["skills"] = ["Python", "Azure", "FastAPI", "React", "Docker"]
    resp = await async_client.put("/api/v1/profile", headers=auth_headers, json=updated)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["full_name"] == "Verified Candidate"
    assert "FastAPI" in res_data["skills"]

    # 3. Upload resume
    fake_resume = b"%PDF-1.4 Mock resume content for candidate evaluation."
    files = {"file": ("test_resume.pdf", fake_resume, "application/pdf")}
    resp = await async_client.post("/api/v1/profile/resume", headers=auth_headers, files=files)
    assert resp.status_code == 200
    upload_res = resp.json()
    assert upload_res["filename"] == "test_resume.pdf"
    assert upload_res["file_size_bytes"] == len(fake_resume)


@pytest.mark.asyncio
async def test_idor_cross_user_isolation(async_client: AsyncClient):
    # User A headers
    user_a = UserPrincipal(user_id="user_a@test.com", email="user_a@test.com", full_name="User A")
    token_a = create_access_token(user_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User B headers
    user_b = UserPrincipal(user_id="user_b@test.com", email="user_b@test.com", full_name="User B")
    token_b = create_access_token(user_b)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Ingest email for User A
    eml_a = b"""From: recruiter@corp.com
To: user_a@test.com
Subject: Software Engineer Job Offer
Date: Sat, 19 Sep 2026 10:00:00 +0000
Content-Type: text/plain

We are pleased to offer you a Software Engineer position at Corp.
"""
    resp_upload = await async_client.post(
        "/api/v1/emails/import-eml",
        headers=headers_a,
        files={"file": ("offer.eml", eml_a, "message/rfc822")},
    )
    assert resp_upload.status_code == 200
    email_a_id = resp_upload.json()["id"]

    # User A can fetch it
    resp_a = await async_client.get(f"/api/v1/emails/{email_a_id}", headers=headers_a)
    assert resp_a.status_code == 200

    # User B MUST NOT be able to fetch User A's email (404/403)
    resp_b = await async_client.get(f"/api/v1/emails/{email_a_id}", headers=headers_b)
    assert resp_b.status_code in (404, 403)
