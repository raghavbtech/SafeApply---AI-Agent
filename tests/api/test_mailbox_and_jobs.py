"""Tests for mailbox, spam routing, audit, and job agent endpoints."""

import pytest
from httpx import AsyncClient
from backend.adapters.repository import RepositoryAdapter


@pytest.mark.asyncio
async def test_mailbox_and_email_lifecycle(async_client: AsyncClient, auth_headers: dict, demo_principal):
    user_id = demo_principal.user_id

    # Ingest a sample email into repository
    sample_email = {
        "id": "test_msg_001",
        "message_id": "<test-msg-001@safeapply.local>",
        "sender": "recruiter@razorpay.com",
        "sender_name": "Razorpay Talent Team",
        "subject": "Interview for Software Engineer Internship",
        "date": "2026-09-19",
        "body": "We are pleased to invite you for a Software Engineer role at Razorpay. Location: Bengaluru. Required skills: Python, SQL, REST APIs.",
        "company_name": "Razorpay",
        "role_title": "Software Engineer Intern",
        "is_recruitment": True,
        "folder": "inbox",
        "status": "unscanned",
    }
    RepositoryAdapter.save_emails([sample_email], user_id=user_id)

    # 1. List emails
    resp = await async_client.get("/api/v1/emails?folder=inbox", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    found = any(e["id"] == "test_msg_001" for e in data["items"])
    assert found is True

    # 2. Get email detail
    resp = await async_client.get("/api/v1/emails/test_msg_001", headers=auth_headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["company_name"] == "Razorpay"

    # 3. Analyze email
    resp = await async_client.post("/api/v1/emails/test_msg_001/analyze?fast_mode=true", headers=auth_headers)
    assert resp.status_code == 200
    analysis = resp.json()
    assert "risk_level" in analysis
    assert "risk_score" in analysis

    # 4. Move to spam
    resp = await async_client.post(
        "/api/v1/emails/test_msg_001/spam",
        headers=auth_headers,
        json={"reason": "Testing manual quarantine"},
    )
    assert resp.status_code == 200
    spam_res = resp.json()
    assert spam_res["ok"] is True

    # Check it now appears in spam folder
    resp = await async_client.get("/api/v1/emails?folder=spam", headers=auth_headers)
    assert resp.status_code == 200
    spam_items = resp.json()["items"]
    assert any(e["id"] == "test_msg_001" for e in spam_items)

    # 5. Restore from spam
    resp = await async_client.post("/api/v1/emails/test_msg_001/restore", headers=auth_headers)
    assert resp.status_code == 200
    restore_res = resp.json()
    assert restore_res["ok"] is True

    # 6. Check audit log and chain
    resp = await async_client.get("/api/v1/audit", headers=auth_headers)
    assert resp.status_code == 200
    audits = resp.json()
    assert len(audits) >= 2

    resp = await async_client.get("/api/v1/audit/verify", headers=auth_headers)
    assert resp.status_code == 200
    chain = resp.json()
    assert chain["valid"] is True


@pytest.mark.asyncio
async def test_job_agent_flow(async_client: AsyncClient, auth_headers: dict, demo_principal):
    user_id = demo_principal.user_id

    # Create job email
    job_email = {
        "id": "job_msg_002",
        "sender": "careers@google.com",
        "sender_name": "Google Careers",
        "subject": "Google Software Engineering Intern Opportunity",
        "date": "2026-09-19",
        "body": "Google is hiring Software Engineering Interns in Hyderabad. Skills required: Python, Algorithms, Data Structures, Git. Please review our portal.",
        "company_name": "Google",
        "role_title": "Software Engineering Intern",
        "is_recruitment": True,
        "folder": "inbox",
        "status": "unscanned",
    }
    RepositoryAdapter.save_emails([job_email], user_id=user_id)

    # 1. Preview job spec & match
    resp = await async_client.get("/api/v1/jobs/job_msg_002/preview", headers=auth_headers)
    assert resp.status_code == 200
    preview = resp.json()
    assert "job_spec" in preview
    assert "match_evaluation" in preview

    # 2. Generate application draft
    resp = await async_client.post("/api/v1/jobs/job_msg_002/draft", headers=auth_headers)
    assert resp.status_code == 200
    draft = resp.json()
    assert len(draft["cover_letter"]) > 50
    assert len(draft["recruiter_reply"]) > 50

    # 3. Approve and send application
    resp = await async_client.post(
        "/api/v1/jobs/job_msg_002/send",
        headers=auth_headers,
        json={
            "approved_cover_letter": draft["cover_letter"],
            "approved_recruiter_reply": draft["recruiter_reply"],
        },
    )
    assert resp.status_code == 200
    app_record = resp.json()
    assert "submission_id" in app_record
    assert app_record["company_name"] == "Google"

    # 4. Check application history
    resp = await async_client.get("/api/v1/applications", headers=auth_headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) >= 1
    assert any(a["email_id"] == "job_msg_002" for a in apps)
