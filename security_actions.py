"""
SafeApply - Security Actions & Threat Quarantine Module

Handles:
1. Moving high/critical risk recruitment scam emails into the Quarantine Vault
2. Tamper-evident security audit logging
3. Restoring accidentally quarantined items
4. Step-by-step verification checklist generation for ambiguous offers
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

VAULT_FILE = os.path.join(os.path.dirname(__file__), "quarantine_vault.json")


def load_vault() -> List[Dict[str, Any]]:
    """Load quarantined items from storage."""
    if os.path.exists(VAULT_FILE):
        try:
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_vault(items: List[Dict[str, Any]]) -> None:
    """Save quarantined items to storage."""
    with open(VAULT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


from azure_db import (
    db_write_audit,
    db_fetch_audit,
    db_update_email_fields,
    DEFAULT_USER_ID,
)


def quarantine_email(
    email: Dict[str, Any],
    reason: str = "Recruitment scam indicators detected",
    user_confirmed: bool = True,
) -> Dict[str, Any]:
    """
    Quarantine a high-risk scam email.
    Creates a tamper-evident cryptographic security audit record and updates state.
    """
    vault = load_vault()
    
    # Extract indicators from analysis if present
    analysis = email.get("analysis") or {}
    red_flags = analysis.get("red_flags", [])
    rag_patterns = analysis.get("rag_scam_patterns", [])
    extracted = analysis.get("extracted_data", {})
    
    quarantine_record = {
        "record_id": f"QRT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{email['id']}",
        "email_id": email["id"],
        "sender": email.get("sender", ""),
        "sender_name": email.get("sender_name", ""),
        "subject": email.get("subject", ""),
        "claimed_company": email.get("company_name", "Unknown"),
        "role_title": email.get("role_title", "Not Specified"),
        "quarantined_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "risk_score": email.get("risk_score", 90),
        "risk_level": email.get("risk_level", "High"),
        "reason": reason,
        "observed_indicators": red_flags,
        "rag_pattern_categories": [p.get("category") for p in rag_patterns if isinstance(p, dict)],
        "user_confirmed": user_confirmed,
        "original_body_preview": (email.get("body", "")[:300] + "...") if len(email.get("body", "")) > 300 else email.get("body", ""),
    }

    # Store in Azure Cosmos DB audit log with cryptographic hash-chaining
    try:
        audit_entry = db_write_audit("quarantine", email["id"], quarantine_record)
        if isinstance(audit_entry, dict) and "record_hash" in audit_entry:
            quarantine_record["record_hash"] = audit_entry["record_hash"]
            quarantine_record["prev_record_hash"] = audit_entry.get("prev_hash", "GENESIS")
    except Exception as exc:  # noqa: BLE001
        print(f"[security_actions] audit logging warning: {exc}")

    try:
        db_update_email_fields(email["id"], {"status": "quarantined", "folder": "spam"})
    except Exception:  # noqa: BLE001
        pass

    # Upsert in JSON vault for local backup
    existing_idx = next((i for i, r in enumerate(vault) if r["email_id"] == email["id"]), None)
    if existing_idx is not None:
        vault[existing_idx] = quarantine_record
    else:
        vault.insert(0, quarantine_record)

    save_vault(vault)
    email["status"] = "quarantined"
    return quarantine_record


def restore_email_from_vault(email_id: str, mailbox_manager=None) -> bool:
    """Restore an email from quarantine back to active inbox."""
    vault = load_vault()
    try:
        db_update_email_fields(email_id, {"status": "scanned", "folder": "inbox"})
        db_write_audit("restore", email_id, {"restored_at": datetime.now().isoformat()})
    except Exception:  # noqa: BLE001
        pass

    updated_vault = [r for r in vault if r["email_id"] != email_id]
    save_vault(updated_vault)
    if mailbox_manager:
        mailbox_manager.update_email_status(email_id, "scanned")
    return True


def get_quarantined_records() -> List[Dict[str, Any]]:
    """Retrieve all quarantined records for UI display (from Azure Cosmos DB audit log)."""
    try:
        audits = db_fetch_audit()
        records = []
        for a in audits:
            if a.get("action") == "quarantine" and isinstance(a.get("details"), dict):
                rec = dict(a["details"])
                rec["record_hash"] = a.get("record_hash", "")
                rec["prev_record_hash"] = a.get("prev_hash", "")
                records.append(rec)
        if records:
            return records
    except Exception:  # noqa: BLE001
        pass
    return load_vault()


def generate_verification_checklist(email: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate an actionable step-by-step verification checklist for Medium-risk ambiguous offers.
    Helps the user verify authenticity before proceeding.
    """
    analysis = email.get("analysis") or {}
    domain_check = analysis.get("domain_check", {})
    extracted = analysis.get("extracted_data", {})
    company = email.get("company_name", "the employer")

    checklist = [
        {
            "id": "chk_domain",
            "title": "Verify Recruiter Domain & Identity",
            "description": f"Verify whether the sender domain ({email.get('sender', '').split('@')[-1]}) is the official domain of {company}. Look up their official website independently.",
            "completed": False,
            "risk_type": "Domain Authentication"
        },
        {
            "id": "chk_portal",
            "title": "Search Official Careers Portal",
            "description": f"Visit the official careers site of {company} (e.g., search '{company} careers') and check if the role '{email.get('role_title', 'this opening')}' is officially listed.",
            "completed": False,
            "risk_type": "Job Existence"
        },
        {
            "id": "chk_no_fees",
            "title": "Zero-Fee Policy Verification",
            "description": "Legitimate enterprise employers NEVER request payment for registration, training, laptops, or background verification. Under no circumstances transfer any money.",
            "completed": False,
            "risk_type": "Financial Safety"
        },
        {
            "id": "chk_interview",
            "title": "Validate Interview Process",
            "description": "Legitimate technical roles involve interviews with hiring managers and HR. Beware of offers made solely via Telegram, WhatsApp, or instant selection questionnaires.",
            "completed": False,
            "risk_type": "Recruitment Protocol"
        },
        {
            "id": "chk_privacy",
            "title": "Withhold Sensitive Identity Documents",
            "description": "Do not send high-resolution photos of Aadhaar card, PAN card, passport, or bank statements until an official offer is verified on the employer's corporate portal.",
            "completed": False,
            "risk_type": "Data Privacy"
        }
    ]

    return checklist
