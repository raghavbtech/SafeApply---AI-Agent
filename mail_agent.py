"""
SafeApply - Mail Agent & Inbox Management Module

Handles:
1. Recruitment email ingestion (simulated inbox + custom additions)
2. Recruitment vs non-recruitment email filtering
3. Batch inbox scanning orchestration
4. Email lifecycle management (Unscanned -> Scanned -> Quarantined / Applied)
"""

import os
import re
import copy
from datetime import datetime
from typing import List, Dict, Any, Optional

from agent import analyze_job_offer


# =========================================================
# RECRUITMENT CLASSIFIER HEURISTIC
# =========================================================

RECRUITMENT_KEYWORDS = [
    r"\bjob\b", r"\boffer\b", r"\bintern\b", r"\binternship\b",
    r"\brecruit\b", r"\bhiring\b", r"\bselection\b", r"\bcandidat\b",
    r"\bstipend\b", r"\bsalary\b", r"\bctc\b", r"\blpa\b",
    r"\bcareer\b", r"\bplacement\b", r"\binterview\b", r"\bopening\b",
    r"\bposition\b", r"\bengineer\b", r"\bdeveloper\b", r"\bwork from home\b",
]

NON_RECRUITMENT_INDICATORS = [
    r"\bdigest\b", r"\bnewsletter\b", r"\bunsubscribe\b",
    r"\bgithub notification\b", r"\bsecurity alert\b", r"\bpassword reset\b",
    r"\bpromotional discount\b", r"\bweekly update\b"
]


def is_recruitment_email(subject: str, body: str, sender: str = "") -> bool:
    """
    Determine whether an incoming email is recruitment-related.
    Filters out newsletters, system alerts, and generic notifications.
    """
    text = f"{subject} {body} {sender}".lower()

    recruitment_hits = sum(1 for pat in RECRUITMENT_KEYWORDS if re.search(pat, text))
    non_recruitment_hits = sum(1 for pat in NON_RECRUITMENT_INDICATORS if re.search(pat, text))

    if non_recruitment_hits > 0 and recruitment_hits < 2:
        return False

    return recruitment_hits >= 1


# =========================================================
# DEFAULT SIMULATED INBOX
# =========================================================

DEFAULT_DEMO_EMAILS: List[Dict[str, Any]] = [
    {
        "id": "EML-001",
        "sender": "hr.techcorp@gmail.com",
        "sender_name": "TechCorp India HR Desk",
        "subject": "Urgent: Selection Letter & Placement Confirmation - Software Engineer Intern",
        "date": "2026-09-17 09:15 AM",
        "body": """Congratulations! You are selected as Software Engineer Intern at TechCorp Solutions India.
CTC: INR 8,00,000 per annum (8 LPA).
To confirm your placement slot, you must pay a refundable registration charge of Rs 1,499 via UPI within 2 hours.
Submit payment screenshot to hr.techcorp@gmail.com immediately or your offer will be revoked.
Joining date is 1st of next month.""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "TechCorp Solutions",
        "role_title": "Software Engineer Intern",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-002",
        "sender": "recruitment@amazon-global-careers.net",
        "sender_name": "Amazon Global Hiring Operations",
        "subject": "Direct Selection: Work from Home Data Entry Specialist (INR 75,000/mo)",
        "date": "2026-09-17 10:05 AM",
        "body": """URGENT HIRING: Work from Home 2 hours daily doing copy paste data entry.
Guaranteed payout: INR 75,000 per month plus daily bonus. No interview, no experience needed.
Direct selection letter. Contact hiring director immediately on Telegram @AmazonJobsIndiaDesk.
Your employment package begins immediately upon connecting on Telegram.""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Amazon (Impersonation)",
        "role_title": "Data Entry Specialist",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-003",
        "sender": "logistics-team@cloudscale-hiring-portal.com",
        "sender_name": "CloudScale Welcome Logistics",
        "subject": "Action Required: MacBook Pro Dispatch & Asset Transit Insurance Fee",
        "date": "2026-09-17 10:45 AM",
        "body": """Welcome to CloudScale Systems India!
We are shipping your welcome kit including Apple MacBook Pro M3.
Please transfer refundable transit clearance insurance charge of Rs 5,000 to our courier account.
Also send photos of your front and back Aadhaar card and PAN card for IT asset security compliance.
Contact: logistics-team@cloudscale-hiring-portal.com""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "CloudScale Systems",
        "role_title": "Systems Associate",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-004",
        "sender": "university-recruiting@microsoft.com",
        "sender_name": "Microsoft University Recruiting India",
        "subject": "Offer of Internship: Software Engineering Intern at Microsoft India",
        "date": "2026-09-17 11:20 AM",
        "body": """Dear Candidate,
Following your technical interviews with our engineering team, we are pleased to offer you an internship at Microsoft India (R&D) Pvt. Ltd.
Role: Software Engineering Intern
Stipend: INR 50,000 per month
Location: Hyderabad Campus
Required Skills: Python, Data Structures, Algorithms, Cloud Fundamentals
No fees or security deposits are required at any stage of our recruitment process.
Please review your formal offer letter on the Microsoft Careers Portal: https://careers.microsoft.com.
Sincerely,
University Recruiting Team, Microsoft India
Email: university-recruiting@microsoft.com""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Microsoft India",
        "role_title": "Software Engineering Intern",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-005",
        "sender": "career@infosys.com",
        "sender_name": "Infosys Talent Acquisition",
        "subject": "Offer Letter - Systems Engineer Position at Infosys Limited",
        "date": "2026-09-17 11:45 AM",
        "body": """Dear Candidate,
Congratulations on successfully clearing the InfyTQ certification and technical interview rounds!
Infosys Limited is pleased to offer you the role of Systems Engineer.
Compensation: INR 3,60,000 per annum (3.6 LPA).
Joining location will be Mysore Development Centre for initial training.
Required Skills: Java, Python, SQL, Problem Solving.
Infosys never charges any fee or asks for money deposit from job seekers at any stage of recruitment.
Kindly accept through our candidate portal at https://career.infosys.com within 5 business days.
Warm regards,
Talent Acquisition Team, Infosys Limited""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Infosys Limited",
        "role_title": "Systems Engineer",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-006",
        "sender": "careers@razorpay.com",
        "sender_name": "Razorpay Talent Team",
        "subject": "Engineering Role Opportunity: Software Development Engineer (Backend)",
        "date": "2026-09-17 12:10 PM",
        "body": """Hi Aarav,
We came across your profile and open-source contributions. The Payments Engineering team at Razorpay is looking for a Backend Engineer (SDE-1 / SDE-2).
Role: Software Development Engineer - Backend
Location: Bengaluru (Hybrid)
Compensation: ₹18 - 24 LPA + ESOPs
Key Requirements: Python or Go, REST APIs, Microservices, Distributed Systems, SQL / NoSQL databases.
Our recruitment team does not charge any placement or application fees.
If interested, please reply with your updated resume or apply directly at https://razorpay.com/jobs/backend-engineer/.
Best,
Devi Nair | Tech Talent Partner, Razorpay""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Razorpay",
        "role_title": "Software Development Engineer - Backend",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-007",
        "sender": "founder@stealth-ai-lab.io",
        "sender_name": "Stealth AI Lab",
        "subject": "Freelance Machine Learning Prototype - Quick Turnaround",
        "date": "2026-09-17 12:30 PM",
        "body": """Hi, We are building an AI agent prototype and need someone to help build our LangChain / RAG evaluation pipeline this weekend.
Budget: $1,500 for the task.
Connect with us on Telegram @StealthFounderAI to discuss requirements and get initial sample repo.
No interview, we review your GitHub profile and assign immediately.""",
        "status": "unscanned",
        "is_recruitment": True,
        "company_name": "Stealth AI Lab",
        "role_title": "ML Prototype Contractor",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
    {
        "id": "EML-008",
        "sender": "notifications@github.com",
        "sender_name": "GitHub Notifications",
        "subject": "[GitHub] Security advisory alert: dependencies in your repository",
        "date": "2026-09-17 01:00 PM",
        "body": """Hi @raghavbtech,
GitHub Dependabot detected 1 moderate severity security vulnerability in your repository raghavbtech/SafeApply---AI-Agent.
We recommend upgrading cryptography to version 42.0.0.
To unsubscribe from this digest, change your notification settings on github.com.""",
        "status": "ignored",
        "is_recruitment": False,
        "company_name": "GitHub",
        "role_title": "N/A",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    },
]


# =========================================================
# MAILBOX MANAGER CLASS
# =========================================================

class MailboxManager:
    """
    Manages user mailbox state, message ingestion, scanning, and actions.
    """

    def __init__(self, initial_emails: Optional[List[Dict[str, Any]]] = None):
        if initial_emails is not None:
            self.emails = copy.deepcopy(initial_emails)
        else:
            self.emails = copy.deepcopy(DEFAULT_DEMO_EMAILS)

    def get_all_emails(self) -> List[Dict[str, Any]]:
        """Return all emails in mailbox."""
        return self.emails

    def get_recruitment_emails(self) -> List[Dict[str, Any]]:
        """Return only recruitment-related emails."""
        return [e for e in self.emails if e.get("is_recruitment", True)]

    def get_email_by_id(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific email by ID."""
        for email in self.emails:
            if email["id"] == email_id:
                return email
        return None

    def add_custom_email(
        self,
        sender: str,
        sender_name: str,
        subject: str,
        body: str,
        company_name: str = "",
        role_title: str = ""
    ) -> Dict[str, Any]:
        """
        Ingest a new email into the mailbox.
        Automatically runs recruitment classification.
        """
        new_id = f"EML-{len(self.emails) + 1:03d}"
        now_str = datetime.now().strftime("%Y-%m-%d %I:%M %p")
        is_rec = is_recruitment_email(subject, body, sender)

        new_email = {
            "id": new_id,
            "sender": sender.strip(),
            "sender_name": sender_name.strip() or sender.split("@")[0],
            "subject": subject.strip(),
            "date": now_str,
            "body": body.strip(),
            "status": "unscanned" if is_rec else "ignored",
            "is_recruitment": is_rec,
            "company_name": company_name.strip() or "Unknown",
            "role_title": role_title.strip() or "Not Specified",
            "risk_score": None,
            "risk_level": None,
            "analysis": None,
        }

        self.emails.insert(0, new_email)
        return new_email

    def scan_single_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Run the full SafeApply multi-pillar pipeline on a specific email.
        """
        email = self.get_email_by_id(email_id)
        if not email or not email.get("is_recruitment", True):
            return email

        email["status"] = "scanning"
        try:
            analysis = analyze_job_offer(email["body"])
            email["analysis"] = analysis
            email["risk_score"] = analysis.get("risk_score", 50)
            email["risk_level"] = analysis.get("risk_level", "Medium")
            email["status"] = "scanned"

            # Update extracted company and role if available
            extracted = analysis.get("extracted_data", {})
            if extracted.get("company_name") and email["company_name"] == "Unknown":
                email["company_name"] = extracted["company_name"]
            if extracted.get("job_title") and email["role_title"] == "Not Specified":
                email["role_title"] = extracted["job_title"]

        except Exception as e:
            email["status"] = "error"
            email["error_message"] = str(e)

        return email

    def scan_all_unscanned(self, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Scan all unscanned recruitment emails in the inbox.
        Calls progress_callback(current, total, email) if provided.
        """
        unscanned = [e for e in self.emails if e.get("is_recruitment", True) and e.get("status") == "unscanned"]
        total = len(unscanned)

        for idx, email in enumerate(unscanned):
            if progress_callback:
                progress_callback(idx, total, email)
            self.scan_single_email(email["id"])

        if progress_callback:
            progress_callback(total, total, None)

        return self.emails

    def update_email_status(self, email_id: str, new_status: str):
        """Update the status of an email (e.g., 'quarantined', 'applied')."""
        email = self.get_email_by_id(email_id)
        if email:
            email["status"] = new_status

    def get_mailbox_stats(self) -> Dict[str, int]:
        """Compute inbox summary statistics."""
        recruitment_emails = [e for e in self.emails if e.get("is_recruitment", True)]
        scanned = [e for e in recruitment_emails if e.get("status") == "scanned"]

        scams = [e for e in scanned if e.get("risk_level") in ("High", "Critical")]
        ambiguous = [e for e in scanned if e.get("risk_level") == "Medium"]
        legitimate = [e for e in scanned if e.get("risk_level") == "Low"]
        quarantined = [e for e in self.emails if e.get("status") == "quarantined"]
        applied = [e for e in self.emails if e.get("status") == "applied"]

        return {
            "total_emails": len(self.emails),
            "recruitment_emails": len(recruitment_emails),
            "unscanned": len([e for e in recruitment_emails if e.get("status") == "unscanned"]),
            "scanned": len(scanned),
            "high_risk_scams": len(scams),
            "medium_risk": len(ambiguous),
            "low_risk_legitimate": len(legitimate),
            "quarantined": len(quarantined),
            "applied": len(applied),
        }
