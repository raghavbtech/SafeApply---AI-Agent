"""
SafeApply - Automatic Scan & Risk Routing Engine
=================================================

Takes every unscanned recruitment email in Cosmos, runs the existing
SafeApply analysis pipeline over it, writes the verdict back, and routes the
message:

    Critical / High  -> moved to the real mailbox Junk folder, folder = "spam"
    Medium           -> stays in inbox, flagged for user verification
    Low              -> stays in inbox, offered to the Job Agent

Responsible AI position
-----------------------
Automatic quarantine is a real, irreversible-looking action taken on a user's
mailbox, so three safeguards are non-negotiable:

  1. It is configurable. AUTO_QUARANTINE_ENABLED and AUTO_QUARANTINE_THRESHOLD
     control whether it happens at all and at what score.
  2. It is logged. Every move writes a hash-chained audit record.
  3. It is reversible. restore_from_spam() moves the message back to INBOX
     and restores the SafeApply folder state.

The message is moved, never deleted. SafeApply does not have, and should not
have, the ability to destroy a user's mail.
"""

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv

from agent import analyze_job_offer
from azure_db import (
    DEFAULT_USER_ID,
    db_fetch_all_emails,
    db_fetch_email,
    db_update_email_fields,
    db_write_audit,
)
from mail_sync import (
    close_imap,
    find_junk_folder,
    get_mail_credentials,
    open_imap,
)

from job_agent import (
    extract_job_spec,
    generate_application_package,
    submit_application,
    load_candidate_profile,
)

load_dotenv()


AUTO_QUARANTINE_ENABLED = os.getenv("AUTO_QUARANTINE_ENABLED", "true").lower() == "true"
AUTO_QUARANTINE_THRESHOLD = int(os.getenv("AUTO_QUARANTINE_THRESHOLD", "65"))
AUTO_APPLY_ENABLED = os.getenv("AUTO_APPLY_ENABLED", "true").lower() == "true"
AUTO_APPLY_MAX_RISK_SCORE = int(os.getenv("AUTO_APPLY_MAX_RISK_SCORE", "45"))

# Risk levels that trigger the quarantine path when auto-quarantine is on.
QUARANTINE_LEVELS = {"High", "Critical"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =========================================================
# ANALYSIS INPUT
# =========================================================

def build_analysis_context(email: Dict[str, Any]) -> str:
    """
    Compose the full message context for the security pipeline.

    Addresses Flaw 5: the sender address is frequently the single strongest
    signal ("microsoft-careers@gmail.com"), and it lives in the headers, not
    the body. Analysing the body alone throws that signal away.
    """
    return (
        f"From: {email.get('sender_name', '')} <{email.get('sender', '')}>\n"
        f"Subject: {email.get('subject', '')}\n"
        f"Date: {email.get('date', '')}\n\n"
        f"{email.get('body', '')}"
    )


# =========================================================
# MAILBOX ACTIONS
# =========================================================

def _move_uid(mail, uid: str, destination: str) -> bool:
    """
    Move one message by UID. Prefers RFC 6851 UID MOVE, which is atomic and
    supported by Gmail and Outlook. Falls back to COPY + \\Deleted + EXPUNGE
    for servers without MOVE.
    """
    capabilities = {c.upper() for c in getattr(mail, "capabilities", ())}

    if "MOVE" in capabilities:
        typ, _ = mail.uid("MOVE", uid, f'"{destination}"')
        return typ == "OK"

    typ, _ = mail.uid("COPY", uid, f'"{destination}"')
    if typ != "OK":
        return False

    mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
    mail.expunge()
    return True


def move_to_spam(
    doc_id: str,
    reason: str,
    user_id: str = DEFAULT_USER_ID,
    automated: bool = False,
) -> Dict[str, Any]:
    """
    Move a message into the mailbox's real Junk folder and mark it 'spam' in
    Cosmos. Returns a result dict; the Cosmos state is updated either way so
    the UI always reflects what actually happened.
    """
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found in database."}

    uid = email.get("imap_uid")
    creds = get_mail_credentials()
    moved = False
    error = ""

    if uid and creds["username"] and creds["password"]:
        mail = None
        try:
            mail = open_imap(
                provider=creds["provider"],
                username=creds["username"],
                password=creds["password"],
                server=creds.get("server"),
                port=creds.get("port", 993),
                readonly=False,
            )
            junk = find_junk_folder(mail, creds["provider"])
            moved = _move_uid(mail, str(uid), junk)
            if not moved:
                error = f"Server refused the move to '{junk}'."
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        finally:
            close_imap(mail)
    else:
        error = "No IMAP UID or credentials; quarantined in SafeApply only."

    db_update_email_fields(
        doc_id,
        {
            "folder": "spam",
            "mailbox_action": "moved_to_junk" if moved else "move_failed",
            "quarantine_reason": reason,
            "quarantined_at": _utcnow(),
            "quarantined_automatically": automated,
        },
        user_id,
    )

    db_write_audit(
        action="auto_quarantine" if automated else "manual_quarantine",
        email_doc_id=doc_id,
        details={
            "subject": email.get("subject"),
            "sender": email.get("sender"),
            "risk_level": email.get("risk_level"),
            "risk_score": email.get("risk_score"),
            "reason": reason,
            "mailbox_move_succeeded": moved,
            "mailbox_error": error,
        },
        user_id=user_id,
    )

    return {"ok": True, "mailbox_moved": moved, "error": error}


def restore_from_spam(doc_id: str, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """
    Move a quarantined message back to INBOX. This is the reversibility
    guarantee that makes automatic quarantine acceptable.
    """
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found in database."}

    creds = get_mail_credentials()
    restored = False
    error = ""

    if email.get("mailbox_action") == "moved_to_junk" and creds["username"]:
        mail = None
        try:
            mail = open_imap(
                provider=creds["provider"],
                username=creds["username"],
                password=creds["password"],
                server=creds.get("server"),
                port=creds.get("port", 993),
                readonly=False,
            )
            junk = find_junk_folder(mail, creds["provider"])
            mail.select(junk, readonly=False)

            # The UID changes when a message moves between folders, so find
            # the message again by its stable Message-ID header.
            message_id = email.get("message_id", "")
            target_uid = None
            if message_id:
                typ, data = mail.uid("SEARCH", None, f'HEADER Message-ID "{message_id}"')
                if typ == "OK" and data and data[0]:
                    target_uid = data[0].split()[0].decode()

            if target_uid:
                restored = _move_uid(mail, target_uid, "INBOX")
            else:
                error = "Could not locate the message in the Junk folder."
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        finally:
            close_imap(mail)

    db_update_email_fields(
        doc_id,
        {
            "folder": "inbox",
            "mailbox_action": "restored" if restored else email.get("mailbox_action", "none"),
            "restored_at": _utcnow(),
        },
        user_id,
    )

    db_write_audit(
        action="restore_from_spam",
        email_doc_id=doc_id,
        details={
            "subject": email.get("subject"),
            "mailbox_restore_succeeded": restored,
            "mailbox_error": error,
        },
        user_id=user_id,
    )

    return {"ok": True, "mailbox_restored": restored, "error": error}


# =========================================================
# SCAN + ROUTE
# =========================================================

def apply_to_email(doc_id: str, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """
    Automatically prepares application package, attaches resume, reverts back
    to recruiter, and updates email state to 'applied' in Azure Cosmos DB.
    """
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found."}

    try:
        profile = load_candidate_profile()
        job_spec = extract_job_spec(email.get("body", ""), email)
        app_pkg = generate_application_package(job_spec, profile, fast_mode=True)
        sub_rec = submit_application(
            email_id=doc_id,
            job_spec=job_spec,
            application_package={
                "cover_letter": app_pkg.get("cover_letter", ""),
                "recruiter_reply": app_pkg.get("recruiter_reply", ""),
            },
            candidate_profile=profile,
            email_data=email,
        )

        db_update_email_fields(
            doc_id,
            {
                "status": "applied",
                "user_decision": "applied",
                "applied_at": _utcnow(),
                "submission_id": sub_rec.get("submission_id"),
                "application_package": {
                    "cover_letter": app_pkg.get("cover_letter", ""),
                    "recruiter_reply": app_pkg.get("recruiter_reply", ""),
                },
            },
            user_id=user_id,
        )

        db_write_audit(
            action="auto_apply",
            email_doc_id=doc_id,
            details={
                "company_name": job_spec.get("company_name"),
                "role_title": job_spec.get("role_title"),
                "submission_id": sub_rec.get("submission_id"),
                "dispatch_status": sub_rec.get("status"),
            },
            user_id=user_id,
        )

        return {
            "ok": True,
            "submission_id": sub_rec.get("submission_id"),
            "company_name": job_spec.get("company_name"),
            "role_title": job_spec.get("role_title"),
            "dispatch_status": sub_rec.get("status"),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[auto_scan] Auto-apply failed for {doc_id}: {exc}")
        return {"ok": False, "error": str(exc)}


def auto_apply_all_low_risk(user_id: str = DEFAULT_USER_ID) -> List[Dict[str, Any]]:
    """
    Finds all existing Low risk or safe recruitment emails in Cosmos DB that have not
    yet been applied to, and automatically executes application packages and dispatches responses for them.
    """
    emails = db_fetch_all_emails(user_id, folder="inbox")
    unapplied = []
    for e in emails:
        if e.get("user_decision") == "applied" or e.get("status") == "applied":
            continue
        r_level = e.get("risk_level", "Medium")
        r_score = e.get("risk_score", 50)
        flags_text = " ".join(str(f).lower() for f in (e.get("analysis") or {}).get("identified_red_flags", []))
        has_severe = any(
            kw in flags_text for kw in ("upfront", "fee", "payment", "money", "check", "cheque", "crypto", "bitcoin", "telegram", "whatsapp", "bank account")
        )
        if (r_level == "Low" or r_score <= AUTO_APPLY_MAX_RISK_SCORE) and not has_severe:
            unapplied.append(e)

    results = []
    for email in unapplied:
        res = apply_to_email(email["id"], user_id=user_id)
        results.append(res)
    return results


def scan_and_route_email(
    doc_id: str,
    user_id: str = DEFAULT_USER_ID,
    allow_auto_quarantine: Optional[bool] = None,
    allow_auto_apply: Optional[bool] = None,
) -> Dict[str, Any]:
    """Analyse one stored email, persist the verdict, and route it."""
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found."}

    if not email.get("is_recruitment", True):
        return {"ok": False, "error": "Not a recruitment email; skipped."}

    auto = AUTO_QUARANTINE_ENABLED if allow_auto_quarantine is None else allow_auto_quarantine

    try:
        analysis = analyze_job_offer(build_analysis_context(email), fast_mode=True)
    except Exception as exc:  # noqa: BLE001
        db_update_email_fields(
            doc_id, {"status": "error", "error_message": str(exc)}, user_id
        )
        return {"ok": False, "error": f"Analysis failed: {exc}"}

    risk_level = analysis.get("risk_level", "Medium")
    risk_score = analysis.get("risk_score", 50)
    extracted = analysis.get("extracted_data", {}) or {}

    updates: Dict[str, Any] = {
        "status": "scanned",
        "risk_level": risk_level,
        "risk_score": risk_score,
        "analysis": analysis,
        "scanned_at": _utcnow(),
    }

    # Only overwrite placeholders. Never invent values the email did not
    # contain (Flaw 9).
    if extracted.get("company_name") and email.get("company_name") in ("Unknown", "", None):
        updates["company_name"] = extracted["company_name"]
    if extracted.get("job_title") and email.get("role_title") in ("Not Specified", "", None):
        updates["role_title"] = extracted["job_title"]

    db_update_email_fields(doc_id, updates, user_id)

    db_write_audit(
        action="auto_scan",
        email_doc_id=doc_id,
        details={
            "subject": email.get("subject"),
            "sender": email.get("sender"),
            "risk_level": risk_level,
            "risk_score": risk_score,
            "execution_mode": analysis.get("execution_mode"),
        },
        user_id=user_id,
    )

    quarantined = False
    should_quarantine = (
        auto
        and risk_level in QUARANTINE_LEVELS
        and risk_score >= AUTO_QUARANTINE_THRESHOLD
    )

    if should_quarantine:
        flags = analysis.get("identified_red_flags", [])
        reason = (
            f"Automatic quarantine at {risk_score}/100 ({risk_level}). "
            + ("Leading indicator: " + str(flags[0]) if flags else "Multiple scam indicators.")
        )
        result = move_to_spam(doc_id, reason, user_id, automated=True)
        quarantined = result.get("ok", False)

    # Auto-apply if risk level is Low or score is below threshold without severe scam flags
    applied = False
    submission_id = None
    auto_apply = AUTO_APPLY_ENABLED if allow_auto_apply is None else allow_auto_apply

    flags_text = " ".join(str(f).lower() for f in analysis.get("identified_red_flags", []))
    has_severe_scam_indicator = any(
        kw in flags_text for kw in ("upfront", "fee", "payment", "money", "check", "cheque", "crypto", "bitcoin", "telegram", "whatsapp", "bank account")
    )
    is_safe_for_auto_apply = (
        (risk_level == "Low" or risk_score <= AUTO_APPLY_MAX_RISK_SCORE)
        and not quarantined
        and not has_severe_scam_indicator
    )

    if is_safe_for_auto_apply and auto_apply:
        apply_res = apply_to_email(doc_id, user_id=user_id)
        if apply_res.get("ok"):
            applied = True
            submission_id = apply_res.get("submission_id")

    return {
        "ok": True,
        "doc_id": doc_id,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "quarantined": quarantined,
        "applied": applied,
        "submission_id": submission_id,
        "subject": email.get("subject"),
    }


def scan_all_unscanned(
    user_id: str = DEFAULT_USER_ID,
    limit: int = 50,
    progress: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    allow_auto_quarantine: Optional[bool] = None,
    allow_auto_apply: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Scan every unscanned recruitment email for this user.

    `progress(index, total, result)` is called after each message so the
    Streamlit UI can drive a progress bar.
    """
    pending = [
        e for e in db_fetch_all_emails(user_id, status="unscanned")
        if e.get("is_recruitment", True)
    ][:limit]

    results: List[Dict[str, Any]] = []
    total = len(pending)

    for index, email in enumerate(pending):
        result = scan_and_route_email(
            email["id"],
            user_id,
            allow_auto_quarantine=allow_auto_quarantine,
            allow_auto_apply=allow_auto_apply,
        )
        results.append(result)
        if progress:
            progress(index + 1, total, result)

    return results


if __name__ == "__main__":
    print(f"Auto-quarantine enabled: {AUTO_QUARANTINE_ENABLED} "
          f"(threshold {AUTO_QUARANTINE_THRESHOLD})")
    for row in scan_all_unscanned(limit=10):
        print(row)