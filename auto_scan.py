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
import re
import email as email_pkg
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
    get_selected_uidvalidity,
    mailbox_account_id,
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
    capabilities = {
        c.decode().upper() if isinstance(c, bytes) else str(c).upper()
        for c in getattr(mail, "capabilities", ())
    }

    if "MOVE" in capabilities:
        typ, _ = mail.uid("MOVE", uid, f'"{destination}"')
        return typ == "OK"

    typ, _ = mail.uid("COPY", uid, f'"{destination}"')
    if typ != "OK":
        return False

    typ, _ = mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
    if typ != "OK":
        return False
    typ, _ = mail.expunge()
    return typ == "OK"


def _select_folder_uidvalidity(mail, folder: str, readonly: bool = False) -> Optional[str]:
    typ, _ = mail.select(folder, readonly=readonly)
    if typ != "OK":
        return None
    return get_selected_uidvalidity(mail)


def _message_id_from_uid(mail, uid: str) -> Optional[str]:
    typ, data = mail.uid(
        "FETCH", str(uid), "(UID BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])"
    )
    if typ != "OK" or not data:
        return None
    for item in data:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
            message = email_pkg.message_from_bytes(item[1])
            return (message.get("Message-ID", "") or "").strip() or None
    return None


def _find_unique_message_id(mail, message_id: str) -> Optional[str]:
    typ, data = mail.uid("SEARCH", None, f'HEADER Message-ID "{message_id}"')
    if typ != "OK" or not data or not data[0]:
        return None
    matches = data[0].split()
    return matches[0].decode() if len(matches) == 1 and isinstance(matches[0], bytes) else (
        str(matches[0]) if len(matches) == 1 else None
    )


def _resolve_source_uid(mail, email: Dict[str, Any], account_id: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve one exact source message; never accept a bare UID as global identity."""
    stored_account = email.get("mailbox_account_id")
    if stored_account and stored_account != account_id:
        return None, "The email belongs to a different connected mailbox."

    source_folder = str(email.get("source_folder") or "INBOX")
    current_uidvalidity = _select_folder_uidvalidity(mail, source_folder, readonly=False)
    stored_uidvalidity = email.get("source_uidvalidity")
    if stored_uidvalidity and current_uidvalidity and str(stored_uidvalidity) != str(current_uidvalidity):
        return None, "The saved mailbox location is stale; no message was moved."

    uid = str(email.get("imap_uid") or "").strip()
    message_id = str(email.get("message_id") or "").strip()
    if uid:
        found_message_id = _message_id_from_uid(mail, uid)
        if found_message_id is not None:
            if message_id and found_message_id != message_id:
                return None, "The saved message identity does not match this mailbox message."
            return uid, None
        if stored_uidvalidity:
            return None, "The saved message is no longer present at its verified mailbox location."

    if message_id:
        resolved = _find_unique_message_id(mail, message_id)
        if resolved:
            return resolved, None
        return None, "Could not uniquely locate the original Gmail message."
    return None, "No linked Gmail message is available for this email."


def move_to_spam(
    doc_id: str,
    reason: str,
    user_id: str = DEFAULT_USER_ID,
    automated: bool = False,
    credentials: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Move a message into the mailbox's real Junk folder and mark it 'spam' in
    Cosmos. Returns a result dict; the Cosmos state is updated either way so
    the UI always reflects what actually happened.
    """
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found in database."}

    if email.get("mailbox_action") == "moved_to_spam" and email.get("folder") == "spam":
        return {"ok": True, "mailbox_moved": True, "local_quarantined": True, "error": None}

    uid = email.get("imap_uid")
    if credentials is None:
        from backend.adapters.mail_provider import MailProviderAdapter
        credentials = MailProviderAdapter.get_decrypted_credentials(user_id)
    creds = credentials or {}
    moved = False
    error = ""
    provider_folder = None
    provider_uidvalidity = None

    has_linked_identity = bool(uid or (email.get("message_id") and email.get("mailbox_account_id")))
    if has_linked_identity and creds.get("username") and (creds.get("password") or creds.get("password_or_token")):
        mail = None
        try:
            mail = open_imap(
                provider=creds["provider"],
                username=creds["username"],
                password=creds.get("password") or creds.get("password_or_token"),
                server=creds.get("server"),
                port=creds.get("port", 993),
                readonly=False,
            )
            resolved_uid, identity_error = _resolve_source_uid(
                mail, email, mailbox_account_id(creds)
            )
            if identity_error:
                error = identity_error
            else:
                junk = find_junk_folder(mail, creds.get("provider", "Gmail"))
                moved = _move_uid(mail, str(resolved_uid), junk)
                provider_folder = junk if moved else None
                provider_uidvalidity = _select_folder_uidvalidity(mail, junk, readonly=True) if moved else None
            if not moved:
                error = error or "The mailbox refused the move to Spam."
        except Exception as exc:  # noqa: BLE001
            error = "Mailbox movement failed. Check the connected mailbox."
        finally:
            close_imap(mail)
    else:
        error = (
            "No linked Gmail message is available; quarantined in SafeApply only."
            if not has_linked_identity
            else "No connected Gmail message; quarantined in SafeApply only."
        )

    local_updated = False
    try:
        local_updated = bool(db_update_email_fields(
            doc_id,
            {
                "status": "quarantined",
                "folder": "spam",
                "mailbox_action": "moved_to_spam" if moved else ("local_only" if not uid else "move_failed"),
                "provider_folder": provider_folder,
                "provider_uidvalidity": provider_uidvalidity,
                "quarantine_reason": reason,
                "quarantined_at": _utcnow(),
                "quarantined_automatically": automated,
            },
            user_id,
        ))
    except Exception:
        error = "Mailbox result was received, but SafeApply could not save it."

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

    return {"ok": local_updated, "mailbox_moved": moved, "local_quarantined": local_updated, "error": error or None}


def restore_from_spam(doc_id: str, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
    """
    Move a quarantined message back to INBOX. This is the reversibility
    guarantee that makes automatic quarantine acceptable.
    """
    email = db_fetch_email(doc_id, user_id)
    if not email:
        return {"ok": False, "error": "Email not found in database."}

    if email.get("mailbox_action") not in {"moved_to_spam", "moved_to_junk"}:
        updated = bool(db_update_email_fields(
            doc_id, {"folder": "inbox", "status": "scanned", "mailbox_action": "restored", "restored_at": _utcnow()}, user_id
        ))
        return {"ok": updated, "mailbox_restored": False, "error": None if updated else "Could not restore local quarantine."}

    from backend.adapters.mail_provider import MailProviderAdapter
    creds = MailProviderAdapter.get_decrypted_credentials(user_id)
    restored = False
    error = ""

    if creds and creds.get("username") and (creds.get("password") or creds.get("password_or_token")):
        mail = None
        try:
            stored_account = email.get("mailbox_account_id")
            if stored_account and stored_account != mailbox_account_id(creds):
                return {"ok": False, "mailbox_restored": False, "error": "The email belongs to a different connected mailbox."}
            mail = open_imap(
                provider=creds["provider"],
                username=creds["username"],
                password=creds.get("password") or creds.get("password_or_token"),
                server=creds.get("server"),
                port=creds.get("port", 993),
                readonly=False,
            )
            junk = str(email.get("provider_folder") or find_junk_folder(mail, creds.get("provider", "Gmail")))
            junk_uidvalidity = _select_folder_uidvalidity(mail, junk, readonly=False)
            stored_uidvalidity = email.get("provider_uidvalidity")
            if stored_uidvalidity and junk_uidvalidity and str(stored_uidvalidity) != str(junk_uidvalidity):
                error = "The saved Spam location is stale; no other message was moved."
                target_uid = None
            else:
                target_uid = None

            # The UID changes when a message moves between folders, so find
            # the message again by its stable Message-ID header.
            message_id = email.get("message_id", "")
            target_uid = None
            if message_id and not error:
                target_uid = _find_unique_message_id(mail, message_id)

            if target_uid:
                restored = _move_uid(mail, target_uid, "INBOX")
            else:
                error = error or "Could not uniquely locate the message in Gmail Spam."
        except Exception as exc:  # noqa: BLE001
            error = "Gmail restoration failed. Check the connected mailbox."
        finally:
            close_imap(mail)

    local_updated = False
    if restored:
        local_updated = bool(db_update_email_fields(
            doc_id, {"folder": "inbox", "mailbox_action": "restored", "restored_at": _utcnow()}, user_id
        ))

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

    return {"ok": local_updated if restored else False, "mailbox_restored": restored and local_updated, "error": error or ("SafeApply could not save the Gmail restore result." if restored else "Gmail restoration was not completed.")}


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
        profile = load_candidate_profile(user_id)
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
            user_id=user_id,
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
        # Only auto-apply to messages that have already been scanned
        if e.get("status") != "scanned":
            continue
        r_level = e.get("risk_level") or "Medium"
        r_score = e.get("risk_score")
        if r_score is None:
            r_score = 50
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
        (risk_level == "Low" or (risk_score is not None and risk_score <= AUTO_APPLY_MAX_RISK_SCORE))
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