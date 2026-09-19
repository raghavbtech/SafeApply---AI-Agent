"""Tests for candidate profile, resume upload, download, deletion, and IDOR cross-user rejection."""

import pytest
from httpx import AsyncClient
from backend.security.session import SessionStore


@pytest.mark.asyncio
async def test_profile_crud_and_resume(async_client: AsyncClient, auth_headers: dict):
    # 1. Get profile (starts empty for new session)
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

    # 3. Upload valid PDF resume
    fake_resume = b"%PDF-1.4 Mock resume content for candidate evaluation."
    files = {"file": ("test_resume.pdf", fake_resume, "application/pdf")}
    resp = await async_client.post("/api/v1/profile/resume", headers=auth_headers, files=files)
    assert resp.status_code == 200
    upload_res = resp.json()
    assert upload_res["filename"] == "test_resume.pdf"
    assert upload_res["file_size_bytes"] == len(fake_resume)

    # 4. Download resume
    resp_dl = await async_client.get("/api/v1/profile/resume", headers=auth_headers)
    assert resp_dl.status_code == 200
    assert resp_dl.content == fake_resume

    # 5. Delete resume
    resp_del = await async_client.delete("/api/v1/profile/resume", headers=auth_headers)
    assert resp_del.status_code == 200
    assert resp_del.json()["success"] is True

    # 6. Verify resume is deleted
    resp_dl_after = await async_client.get("/api/v1/profile/resume", headers=auth_headers)
    assert resp_dl_after.status_code == 404


@pytest.mark.asyncio
async def test_idor_cross_user_isolation(async_client: AsyncClient):
    # Visitor A session
    _, token_a = SessionStore.create_session(user_agent="client-a")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Visitor B session
    _, token_b = SessionStore.create_session(user_agent="client-b")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Ingest email for Visitor A
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

    # Visitor A can fetch it
    resp_a = await async_client.get(f"/api/v1/emails/{email_a_id}", headers=headers_a)
    assert resp_a.status_code == 200

    # Visitor B MUST NOT be able to fetch Visitor A's email (404/403)
    resp_b = await async_client.get(f"/api/v1/emails/{email_a_id}", headers=headers_b)
    assert resp_b.status_code in (404, 403)
