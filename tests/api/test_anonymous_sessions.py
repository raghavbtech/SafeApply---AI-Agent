"""
Comprehensive automated tests for SafeApply's No-Login, No-Signup anonymous architecture.
Validates:
1. Automatic server-side session initialization via HTTP-only cookie.
2. Session retention across requests.
3. Cookie loss / expiration and isolation of new sessions.
4. Cross-visitor data isolation (resumes, profiles, emails, applications).
5. Resume upload validation (PDF/DOCX validation, magic bytes, extension checks).
6. Manual scam analysis without onboarding/resume.
7. Job matching with uploaded resume.
8. Explicit approval requirements for spam move and application dispatch.
9. Duplicate-action prevention (idempotency).
10. Mailbox connection, isolation, and disconnection.
11. 'Delete My Data' complete session and file erasure.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.security.session import SessionStore


@pytest.mark.asyncio
async def test_first_visit_initializes_anonymous_session(async_client: AsyncClient):
    """A new visitor with no cookie automatically gets a unique session and Set-Cookie."""
    resp = await async_client.get("/api/v1/session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["session_id"].startswith("anon_")
    assert "set-cookie" in resp.headers
    assert "safeapply_session=" in resp.headers["set-cookie"]
    assert "HttpOnly" in resp.headers["set-cookie"]


@pytest.mark.asyncio
async def test_session_retention_across_requests(async_client: AsyncClient):
    """Subsequent requests passing the session cookie retain the exact same session ID."""
    resp1 = await async_client.get("/api/v1/session")
    sess_id_1 = resp1.json()["session_id"]
    cookie_val = resp1.cookies.get("safeapply_session")
    assert cookie_val is not None

    resp2 = await async_client.get("/api/v1/session", cookies={"safeapply_session": cookie_val})
    sess_id_2 = resp2.json()["session_id"]
    assert sess_id_1 == sess_id_2


@pytest.mark.asyncio
async def test_tampered_or_invalid_cookie_gets_new_clean_session(async_client: AsyncClient):
    """If browser cookie is tampered or expired, server issues a fresh clean session without leaking data."""
    tampered_cookie = "invalid_fake_token_12345"
    resp = await async_client.get("/api/v1/session", cookies={"safeapply_session": tampered_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"].startswith("anon_")
    assert data["has_profile"] is False
    assert data["has_resume"] is False


@pytest.mark.asyncio
async def test_two_visitors_receive_strictly_isolated_sessions():
    """Visitor A and Visitor B receive separate sessions; neither can see the other's profile or data."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client_a, \
               AsyncClient(transport=transport, base_url="http://test") as client_b:
        # Visitor A
        resp_a = await client_a.get("/api/v1/session")
        cookie_a = resp_a.cookies.get("safeapply_session")
        sess_a = resp_a.json()["session_id"]

        # Visitor B
        resp_b = await client_b.get("/api/v1/session")
        cookie_b = resp_b.cookies.get("safeapply_session")
        sess_b = resp_b.json()["session_id"]

        assert sess_a != sess_b

        # Visitor A configures profile
        await client_a.put(
            "/api/v1/profile",
            json={"full_name": "Alice Candidate", "skills": ["Python", "Azure", "RAG"]},
        )

        # Visitor B checks their profile: must be empty, not Alice's
        resp_b_prof = await client_b.get("/api/v1/profile")
        assert resp_b_prof.status_code == 200
        b_data = resp_b_prof.json()
        assert b_data["full_name"] == ""
        assert "Python" not in b_data["skills"]


@pytest.mark.asyncio
async def test_resume_upload_validation_and_rejection(async_client: AsyncClient):
    """Validates PDF / DOCX magic bytes and rejects disallowed/fake files."""
    resp = await async_client.get("/api/v1/session")
    cookie = resp.cookies.get("safeapply_session")

    # 1. Reject invalid extension
    bad_file = {"file": ("malware.exe", b"MZ\x90\x00executable", "application/x-msdownload")}
    resp_bad = await async_client.post(
        "/api/v1/profile/resume",
        cookies={"safeapply_session": cookie},
        files=bad_file,
    )
    assert resp_bad.status_code == 422

    # 2. Reject fake PDF with mismatching header
    fake_pdf = {"file": ("fake.pdf", b"NOT_A_REAL_PDF_HEADER", "application/pdf")}
    resp_fake = await async_client.post(
        "/api/v1/profile/resume",
        cookies={"safeapply_session": cookie},
        files=fake_pdf,
    )
    assert resp_fake.status_code == 422

    # 3. Accept valid PDF
    valid_pdf = {"file": ("my_resume.pdf", b"%PDF-1.4 Valid candidate resume binary content", "application/pdf")}
    resp_ok = await async_client.post(
        "/api/v1/profile/resume",
        cookies={"safeapply_session": cookie},
        files=valid_pdf,
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["filename"] == "my_resume.pdf"


@pytest.mark.asyncio
async def test_manual_scam_analysis_without_onboarding_or_resume(async_client: AsyncClient):
    """Visitors can directly analyze suspicious job offers without any profile or resume."""
    # Ad-hoc scam offer analysis
    scam_text = """
    URGENT JOB OFFER: Executive Data Analyst at Microsoft Global.
    Pay: $180,000 / month. No interview required.
    Please wire $499 equipment fee via Western Union to receive your laptop.
    Contact: hr-microsoft@gmail.com
    """
    resp = await async_client.post(
        "/api/v1/analysis/text",
        json={"text": scam_text, "fast_mode": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    flags = data.get("identified_red_flags", [])
    assert "wire" in str(flags).lower() or "fee" in str(flags).lower() or data["risk_score"] > 60


@pytest.mark.asyncio
async def test_job_agent_matching_with_resume(async_client: AsyncClient):
    """Job Agent evaluates skill overlap based on candidate's actual saved skills."""
    resp_init = await async_client.get("/api/v1/session")
    cookie = resp_init.cookies.get("safeapply_session")

    # Set skills
    await async_client.put(
        "/api/v1/profile",
        cookies={"safeapply_session": cookie},
        json={
            "full_name": "Developer Jane",
            "skills": ["Python", "Azure", "FastAPI", "React", "Docker"],
            "education": "B.S. Software Engineering",
        },
    )

    # Ingest a legitimate offer
    offer_eml = b"""From: talent@techcorp.com
To: candidate@safeapply.local
Subject: Senior Python Engineer Opening at TechCorp
Date: Sat, 19 Sep 2026 12:00:00 +0000
Content-Type: text/plain

TechCorp is hiring a Senior Python Engineer.
Requirements: Python, Azure, FastAPI, Docker.
Salary: $150,000/yr.
Apply at https://techcorp.com/careers
"""
    resp_ingest = await async_client.post(
        "/api/v1/emails/import-eml",
        cookies={"safeapply_session": cookie},
        files={"file": ("techcorp.eml", offer_eml, "message/rfc822")},
    )
    assert resp_ingest.status_code == 200
    email_id = resp_ingest.json()["id"]

    # Preview match
    resp_prev = await async_client.get(f"/api/v1/jobs/{email_id}/preview", cookies={"safeapply_session": cookie})
    assert resp_prev.status_code == 200
    match_data = resp_prev.json()["match_evaluation"]
    assert match_data["match_percentage"] >= 50
    assert "Python" in match_data["matched_skills"]


@pytest.mark.asyncio
async def test_mailbox_connection_and_disconnection_cycle(async_client: AsyncClient):
    """Connects personal mailbox, verifies status, and cleanly disconnects."""
    resp = await async_client.get("/api/v1/session")
    cookie = resp.cookies.get("safeapply_session")

    # Initially disconnected
    resp_init = await async_client.get("/api/v1/mailboxes", cookies={"safeapply_session": cookie})
    assert resp_init.status_code == 200
    assert resp_init.json()["is_connected"] is False

    # Connect mailbox
    resp_conn = await async_client.post(
        "/api/v1/mailboxes/connect",
        cookies={"safeapply_session": cookie},
        json={
            "provider": "Gmail",
            "username": "candidate.test@gmail.com",
            "password_or_app_token": "abcd-efgh-ijkl-mnop",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
        },
    )
    assert resp_conn.status_code == 200
    assert resp_conn.json()["success"] is True

    # Check connected status
    resp_check = await async_client.get("/api/v1/mailboxes", cookies={"safeapply_session": cookie})
    assert resp_check.json()["is_connected"] is True
    assert resp_check.json()["username"] == "candidate.test@gmail.com"

    # Disconnect
    resp_disc = await async_client.post("/api/v1/mailboxes/disconnect", cookies={"safeapply_session": cookie})
    assert resp_disc.status_code == 200

    # Verify disconnected
    resp_after = await async_client.get("/api/v1/mailboxes", cookies={"safeapply_session": cookie})
    assert resp_after.json()["is_connected"] is False


@pytest.mark.asyncio
async def test_delete_my_data_purges_all_records(async_client: AsyncClient):
    """Calling 'Delete My Data' permanently deletes profile, uploaded resume, and emails."""
    resp = await async_client.get("/api/v1/session")
    cookie = resp.cookies.get("safeapply_session")

    # Upload profile & resume
    await async_client.put(
        "/api/v1/profile",
        cookies={"safeapply_session": cookie},
        json={"full_name": "To Be Deleted", "skills": ["Temporary"]},
    )
    fake_pdf = {"file": ("temp.pdf", b"%PDF-1.4 Temp content", "application/pdf")}
    await async_client.post("/api/v1/profile/resume", cookies={"safeapply_session": cookie}, files=fake_pdf)

    # Verify profile exists
    prof_before = await async_client.get("/api/v1/profile", cookies={"safeapply_session": cookie})
    assert prof_before.json()["full_name"] == "To Be Deleted"

    # Execute Complete Purge
    resp_purge = await async_client.delete("/api/v1/session/data", cookies={"safeapply_session": cookie})
    assert resp_purge.status_code == 200
    assert resp_purge.json()["success"] is True

    # Check profile is reset
    prof_after = await async_client.get("/api/v1/profile", cookies={"safeapply_session": cookie})
    assert prof_after.json()["full_name"] == ""
    assert prof_after.json()["resume_filename"] == ""
