"""
Unit and Integration Tests for SafeApply Autonomous Agent Modules:
- mail_agent.py
- security_actions.py
- job_agent.py
"""

import os
import json

from mail_agent import MailboxManager, is_recruitment_email
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
    DEFAULT_CANDIDATE_PROFILE,
)


def test_recruitment_email_classifier():
    """Test filtering between recruitment and non-recruitment emails."""
    recruitment_text = "We are pleased to offer you an internship as Software Engineer at Microsoft. Stipend: INR 50,000/mo."
    assert is_recruitment_email("Offer Letter", recruitment_text, "recruiting@microsoft.com") is True

    newsletter_text = "GitHub Dependabot detected 1 moderate severity vulnerability. To unsubscribe from this digest, click here."
    assert is_recruitment_email("Weekly Digest", newsletter_text, "notifications@github.com") is False


def test_mailbox_manager_initialization():
    """Test inbox loading and filtering."""
    mgr = MailboxManager()
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
    assert submission["status"] == "Submitted / Active"


if __name__ == "__main__":
    test_recruitment_email_classifier()
    print("PASS: test_recruitment_email_classifier")
    test_mailbox_manager_initialization()
    print("PASS: test_mailbox_manager_initialization")
    test_custom_email_ingestion()
    print("PASS: test_custom_email_ingestion")
    test_security_quarantine_workflow()
    print("PASS: test_security_quarantine_workflow")
    test_verification_checklist_generation()
    print("PASS: test_verification_checklist_generation")
    test_job_agent_spec_extraction_and_matching()
    print("PASS: test_job_agent_spec_extraction_and_matching")
    test_job_agent_package_generation_and_submission()
    print("PASS: test_job_agent_package_generation_and_submission")
    print("\nALL AGENT WORKFLOW TESTS PASSED SUCCESSFULLY!")
