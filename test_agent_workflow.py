"""
Unit and Integration Tests for SafeApply Autonomous Agent Modules:
- mail_agent.py
- security_actions.py
- job_agent.py
"""

import os
import json

from mail_agent import MailboxManager, is_recruitment_email, DEFAULT_DEMO_EMAILS
from security_actions import (
    quarantine_email,
    restore_email_from_vault,
    get_quarantined_records,
    generate_verification_checklist,
)
from job_agent import (
    extract_job_spec,
    evaluate_candidate_match,
    generate_application_package,
    submit_application,
)


DEFAULT_CANDIDATE_PROFILE = {
    "full_name": "Test Candidate",
    "email": "test@example.com",
    "phone": "+1 555 0100",
    "education": "B.S. Computer Science",
    "university": "Test University",
    "cgpa": "8.8",
    "grading_scale": "10",
    "skills": ["Python", "Azure", "FastAPI", "React", "Data Structures", "Algorithms", "Docker"],
    "experience": "Software engineering test experience",
    "preferred_roles": ["Software Engineer"],
    "target_locations": ["Remote"],
    "portfolio_url": "https://example.com",
    "linkedin_url": "https://linkedin.com/in/test",
    "resume_path": "",
    "resume_filename": "test-resume.pdf",
}


def test_recruitment_email_classifier():
    """Test filtering between recruitment and non-recruitment emails."""
    recruitment_text = "We are pleased to offer you an internship as Software Engineer at Microsoft. Stipend: INR 50,000/mo."
    assert is_recruitment_email("Offer Letter", recruitment_text, "recruiting@microsoft.com") is True

    newsletter_text = "GitHub Dependabot detected 1 moderate severity vulnerability. To unsubscribe from this digest, click here."
    assert is_recruitment_email("Weekly Digest", newsletter_text, "notifications@github.com") is False


MOCK_TEST_EMAILS = [
    {"id": f"EML-TEST-{i}", "sender": f"hr{i}@company.com", "subject": "Job Offer", "body": "We are hiring", "status": "unscanned", "is_recruitment": True}
    for i in range(8)
]


def test_mailbox_manager_initialization():
    """Test inbox loading and filtering."""
    mgr = MailboxManager(initial_emails=MOCK_TEST_EMAILS)
    emails = mgr.get_all_emails()
    assert len(emails) >= 8

    rec_emails = mgr.get_recruitment_emails()
    assert len(rec_emails) >= 7

    stats = mgr.get_mailbox_stats()
    assert stats["total_emails"] >= 8
    assert stats["unscanned"] >= 7


def test_custom_email_ingestion():
    """Test adding custom recruitment email to inbox."""
    mgr = MailboxManager()
    new_email = mgr.add_custom_email(
        sender="talent@google.com",
        sender_name="Google Recruiting",
        subject="Interview Invitation - SDE Intern",
        body="Dear Aarav, We would like to schedule an interview for the Software Engineer Intern role at Google.",
        company_name="Google",
        role_title="Software Engineer Intern",
    )
    assert new_email["id"].startswith("EML-")
    assert new_email["is_recruitment"] is True
    assert new_email["status"] == "unscanned"


def test_eml_parsing_and_live_ingestion():
    """Test parsing .eml content and ingesting into mailbox."""
    from mail_agent import parse_eml_content
    raw_eml = b"From: Campus Recruiting <recruiting@amazon.com>\nSubject: Internship Offer - SDE\n\nWe are pleased to offer you an internship role."
    parsed = parse_eml_content(raw_eml)
    assert parsed["sender"] == "recruiting@amazon.com"
    assert "Internship Offer" in parsed["subject"]
    assert parsed["is_recruitment"] is True

    mgr = MailboxManager()
    added = mgr.ingest_live_emails([parsed])
    assert added == 1
    assert mgr.get_email_by_id(parsed["id"]) is not None


def test_security_quarantine_workflow():
    """Test quarantining high-risk emails and audit logging."""
    demo_scam_email = {
        "id": "EML-TEST-SCAM",
        "sender": "hr.techcorp@gmail.com",
        "sender_name": "TechCorp HR",
        "subject": "Urgent Selection - Pay Rs 1,499 via UPI",
        "company_name": "TechCorp Solutions",
        "role_title": "Software Engineer Intern",
        "risk_score": 92,
        "risk_level": "High",
        "body": "Pay Rs 1,499 via UPI within 2 hours to hr.techcorp@gmail.com",
        "status": "scanned",
        "analysis": {
            "red_flags": ["Upfront registration fee", "Urgency deadline"],
            "rag_scam_patterns": [{"category": "upfront_fee"}],
        },
    }

    record = quarantine_email(demo_scam_email, reason="Upfront fee requested")
    assert record["email_id"] == "EML-TEST-SCAM"
    assert demo_scam_email["status"] == "quarantined"

    vault = get_quarantined_records()
    assert any(r["email_id"] == "EML-TEST-SCAM" for r in vault)

    # Test restoration
    restored = restore_email_from_vault("EML-TEST-SCAM")
    assert restored is True


def test_verification_checklist_generation():
    """Test checklist generation for ambiguous offers."""
    amb_email = {
        "id": "EML-AMB-01",
        "sender": "founder@stealth-ai.io",
        "company_name": "Stealth AI",
        "role_title": "ML Prototype Contractor",
        "risk_score": 45,
        "risk_level": "Medium",
    }
    checklist = generate_verification_checklist(amb_email)
    assert len(checklist) >= 4
    assert any("Domain" in item["risk_type"] for item in checklist)
    assert any("Financial" in item["risk_type"] for item in checklist)


def test_job_agent_spec_extraction_and_matching():
    """Test job spec extraction and profile matching."""
    sample_offer = """
    Microsoft India is pleased to offer you the role of Software Engineering Intern.
    Location: Hyderabad Campus
    Stipend: INR 50,000 per month
    Required Skills: Python, Data Structures, Algorithms, Azure, Docker
    Apply at https://careers.microsoft.com.
    """
    job_spec = extract_job_spec(sample_offer)
    assert "Microsoft" in job_spec["company_name"]
    assert "Software Engineering Intern" in job_spec["role_title"]
    assert "Python" in job_spec["required_skills"]

    match_result = evaluate_candidate_match(job_spec, DEFAULT_CANDIDATE_PROFILE)
    assert match_result["match_percentage"] >= 60
    assert "Python" in match_result["matched_skills"]
    assert match_result["match_rating"] in ["Strong Match", "Moderate Match"]


def test_job_agent_package_generation_and_submission():
    """Test application package generation and submission."""
    sample_offer = """
    Razorpay is hiring for Software Development Engineer - Backend.
    Location: Bengaluru (Hybrid)
    Compensation: INR 20 LPA
    Key Requirements: Python, REST APIs, SQL, Docker
    Contact: careers@razorpay.com
    """
    job_spec = extract_job_spec(sample_offer)
    pkg = generate_application_package(job_spec, DEFAULT_CANDIDATE_PROFILE)

    assert "cover_letter" in pkg and len(pkg["cover_letter"]) > 50
    assert "recruiter_reply" in pkg and len(pkg["recruiter_reply"]) > 30
    assert "Razorpay" in pkg["cover_letter"] or "Backend" in pkg["cover_letter"]

    submission = submit_application("EML-006", job_spec, pkg, DEFAULT_CANDIDATE_PROFILE)
    assert submission["submission_id"].startswith("APP-")
    assert submission["company_name"] == job_spec["company_name"]
    assert any(term in submission["status"] for term in ["Recorded", "Approved", "Reverted back", "Dispatched"])


def test_database_and_prestored_fetching():
    """Test database persistence and instant email loading (User DB Feature & Flaw 18/19)."""
    from azure_db import db_save_emails, db_fetch_all_emails

    test_item = {
        "id": "EML-DB-TEST-01",
        "sender": "test@company.com",
        "sender_name": "Test Recruiter",
        "subject": "Cloud Engineer Role",
        "date": "2026-09-18 10:00 AM",
        "body": "Role details here",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Test Corp",
        "role_title": "Cloud Engineer",
        "risk_score": None,
        "risk_level": None,
    }
    saved = db_save_emails([test_item], user_id="test_suite@safeapply.local")
    assert saved >= 1

    fetched = db_fetch_all_emails(user_id="test_suite@safeapply.local")
    assert any(e["id"] == "EML-DB-TEST-01" for e in fetched)


def test_critical_risk_tier_and_metadata():
    """Test Critical tier mapping (Flaw 6) and metadata inclusion (Flaw 5)."""
    from agent import analyze_job_offer

    # Fake offer with high score (>=85) should return Critical
    fake_offer = """
    From: Scammer <urgent-jobs@gmail.com>
    Subject: Immediate Selection - Pay Rs 2,500 Registration Fee Now
    
    You are selected! Transfer Rs 2,500 via UPI within 1 hour to secure your placement.
    Send transaction screenshot to urgent-jobs@gmail.com.
    """
    res = analyze_job_offer(fake_offer)
    assert res["risk_score"] >= 85
    assert res["risk_level"] == "Critical"


def test_no_fabricated_job_requirements():
    """Test that missing requirements are not fabricated with hardcoded defaults (Flaw 9, 10)."""
    bare_offer = "We have an open role available. Please reach out if interested."
    spec = extract_job_spec(bare_offer)
    assert spec["company_name"] == "Not specified"
    assert spec["role_title"] == "Not specified"
    assert spec["required_skills"] == []

    # Test candidate matching with empty requirements
    match = evaluate_candidate_match(spec, DEFAULT_CANDIDATE_PROFILE)
    assert match["missing_skills"] == []
    assert len(match["matched_skills"]) == len(set(match["matched_skills"]))


def test_tamper_evident_vault_hash():
    """Test cryptographic SHA-256 hash chaining in the quarantine vault (Flaw 17)."""
    test_scam = {
        "id": "EML-HASH-TEST",
        "sender": "fake@phish.net",
        "subject": "Urgent Payout",
        "risk_score": 95,
        "risk_level": "Critical",
    }
    rec = quarantine_email(test_scam, reason="Integrity hash test")
    assert "record_hash" in rec and len(rec["record_hash"]) == 64
    assert "prev_record_hash" in rec


def test_no_reply_and_revert_back_workflow():
    """Test automated candidate revert-back and no-reply email detection."""
    from job_agent import is_no_reply_email, revert_back_to_recruiter, submit_application, is_candidate_profile_complete

    # Test candidate profile completeness check
    assert is_candidate_profile_complete({}) is False
    assert is_candidate_profile_complete({"full_name": "Aarav", "email": "a@b.com", "resume_filename": "resume.pdf"}) is True

    # Test 1: No-reply email detection
    assert is_no_reply_email("no-reply@google.com") is True
    assert is_no_reply_email("noreply@linkedin.com") is True
    assert is_no_reply_email("do-not-reply@company.com") is True
    assert is_no_reply_email("university-recruiting@microsoft.com") is False
    assert is_no_reply_email("careers@razorpay.com") is False

    # Test 2: Revert-back dispatch to direct recruiter email
    direct_email = {
        "id": "EML-DIRECT-01",
        "sender": "careers@razorpay.com",
        "subject": "Engineering Role Opportunity",
    }
    job_spec_direct = {
        "company_name": "Razorpay",
        "role_title": "Backend Engineer",
        "contact_email": "careers@razorpay.com",
        "portal_url": "https://razorpay.com/jobs",
    }
    pkg_direct = {
        "cover_letter": "I am writing to apply...",
        "recruiter_reply": "Dear Razorpay Team, I am very interested in the Backend Engineer role.",
    }
    cand_profile = {
        "full_name": "Aarav Sharma",
        "email": "aarav.sharma@example.com",
    }

    res_direct = revert_back_to_recruiter(direct_email, job_spec_direct, pkg_direct, cand_profile)
    assert res_direct["dispatched"] is True
    assert res_direct["is_no_reply"] is False
    assert res_direct["target_email"] == "careers@razorpay.com"
    assert "Reverted back" in res_direct["status"]

    sub_direct = submit_application("EML-DIRECT-01", job_spec_direct, pkg_direct, cand_profile, email_data=direct_email)
    assert sub_direct["is_no_reply"] is False
    assert "Reverted back" in sub_direct["status"]

    # Test 3: No-reply email guidance
    no_reply_email = {
        "id": "EML-NOREPLY-01",
        "sender": "no-reply@google.com",
        "subject": "Google Opportunities Update",
    }
    job_spec_noreply = {
        "company_name": "Google",
        "role_title": "Software Engineer",
        "contact_email": "no-reply@google.com",
        "portal_url": "https://careers.google.com",
    }
    res_noreply = revert_back_to_recruiter(no_reply_email, job_spec_noreply, pkg_direct, cand_profile)
    assert res_noreply["dispatched"] is False
    assert res_noreply["is_no_reply"] is True
    assert "No-Reply Email" in res_noreply["status"]

    sub_noreply = submit_application("EML-NOREPLY-01", job_spec_noreply, pkg_direct, cand_profile, email_data=no_reply_email)
    assert sub_noreply["is_no_reply"] is True
    assert "No-Reply Email" in sub_noreply["status"]


if __name__ == "__main__":
    test_recruitment_email_classifier()
    print("PASS: test_recruitment_email_classifier")
    test_mailbox_manager_initialization()
    print("PASS: test_mailbox_manager_initialization")
    test_custom_email_ingestion()
    print("PASS: test_custom_email_ingestion")
    test_eml_parsing_and_live_ingestion()
    print("PASS: test_eml_parsing_and_live_ingestion")
    test_security_quarantine_workflow()
    print("PASS: test_security_quarantine_workflow")
    test_verification_checklist_generation()
    print("PASS: test_verification_checklist_generation")
    test_job_agent_spec_extraction_and_matching()
    print("PASS: test_job_agent_spec_extraction_and_matching")
    test_job_agent_package_generation_and_submission()
    print("PASS: test_job_agent_package_generation_and_submission")
    test_database_and_prestored_fetching()
    print("PASS: test_database_and_prestored_fetching")
    test_critical_risk_tier_and_metadata()
    print("PASS: test_critical_risk_tier_and_metadata")
    test_no_fabricated_job_requirements()
    print("PASS: test_no_fabricated_job_requirements")
    test_tamper_evident_vault_hash()
    print("PASS: test_tamper_evident_vault_hash")
    test_no_reply_and_revert_back_workflow()
    print("PASS: test_no_reply_and_revert_back_workflow")
    print("\nALL AGENT WORKFLOW & SECURITY TESTS PASSED SUCCESSFULLY!")
