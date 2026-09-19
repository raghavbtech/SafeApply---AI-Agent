"""
SafeApply - Mailbox Sync Engine
================================

Pulls recent messages from the user's real mailbox over IMAP, keeps only the
recruitment-related ones, and stores them in Azure Cosmos DB.

Why UIDs and not sequence numbers
---------------------------------
The original implementation identified messages with `EML-{n}` counters and
IMAP sequence numbers. Sequence numbers are reassigned whenever the mailbox
changes, so the same message could be stored twice under different ids, and a
stored analysis could end up attached to the wrong message. This module uses
IMAP UIDs for fetching and the RFC 5322 Message-ID header for document
identity, which are both stable.

Credential handling
-------------------
The app password is read from the environment, never from the database. That
is a deliberate limitation: a production deployment would use OAuth via
Microsoft Graph or Google, and store nothing but a refresh token in a secrets
vault. Document this in the README rather than storing passwords in Cosmos.
"""

import os
import re
import socket
import imaplib
import email as email_pkg
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from mail_agent import (
    is_recruitment_email,
    _decode_mime_header,
    _extract_body_from_email_message,
)
from azure_db import (
    DEFAULT_USER_ID,
    db_save_emails,
    db_set_state,
    make_email_doc_id,
)

load_dotenv()


PROVIDER_SERVERS: Dict[str, Tuple[str, int]] = {
    "Gmail": ("imap.gmail.com", 993),
    "Outlook / Hotmail": ("outlook.office365.com", 993),
    "Yahoo": ("imap.mail.yahoo.com", 993),
}

# Fallback Junk folder names, used only when the server does not advertise a
# \Junk special-use folder in its LIST response.
FALLBACK_JUNK_FOLDERS: Dict[str, str] = {
    "Gmail": "[Gmail]/Spam",
    "Outlook / Hotmail": "Junk",
    "Yahoo": "Bulk Mail",
}


# =========================================================
# CREDENTIALS
# =========================================================

def get_mail_credentials() -> Dict[str, Any]:
    """
    Read mailbox credentials from the environment.

    Expected .env entries:
        MAIL_PROVIDER=Gmail
        MAIL_USERNAME=you@gmail.com
        MAIL_APP_PASSWORD=abcdefghijklmnop
        MAIL_IMAP_SERVER=            (optional, for custom servers)
        MAIL_IMAP_PORT=993           (optional)
    """
    provider = os.getenv("MAIL_PROVIDER", "Gmail").strip()
    username = os.getenv("MAIL_USERNAME", "").strip()
    password = os.getenv("MAIL_APP_PASSWORD", "").strip()

    if provider == "Gmail":
        # Google shows app passwords as four space-separated groups.
        password = password.replace(" ", "")

    return {
        "provider": provider,
        "username": username,
        "password": password,
        "server": os.getenv("MAIL_IMAP_SERVER", "").strip() or None,
        "port": int(os.getenv("MAIL_IMAP_PORT", "993") or 993),
    }


def is_mail_configured() -> bool:
    creds = get_mail_credentials()
    return bool(creds["username"] and creds["password"])


# =========================================================
# IMAP CONNECTION
# =========================================================

def open_imap(
    provider: str,
    username: str,
    password: str,
    server: Optional[str] = None,
    port: int = 993,
    readonly: bool = True,
) -> imaplib.IMAP4_SSL:
    """
    Open an authenticated IMAP SSL connection with INBOX selected.

    `readonly=False` is required before any flag change or move, so the
    quarantine path opens its own writable connection.
    """
    if server:
        host, imap_port = server, int(port or 993)
    else:
        host, imap_port = PROVIDER_SERVERS.get(provider, ("imap.gmail.com", 993))

    try:
        mail = imaplib.IMAP4_SSL(host, imap_port, timeout=20)
    except socket.gaierror as exc:
        raise ConnectionError(
            f"Could not resolve '{host}'. Check your internet connection."
        ) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise ConnectionError(
            f"Connection to '{host}:{imap_port}' timed out after 20 seconds."
        ) from exc

    try:
        mail.login(username, password)
    except imaplib.IMAP4.error as exc:
        message = str(exc)
        if provider == "Gmail" and "AUTHENTICATIONFAILED" in message.upper():
            raise ConnectionError(
                "Gmail authentication failed. Confirm that: "
                "(1) you are using a 16-character Google App Password, not your "
                "account password; (2) 2-Step Verification is enabled; "
                "(3) IMAP is enabled in Gmail settings."
            ) from exc
        raise ConnectionError(f"IMAP login failed: {message}") from exc

    mail.select("INBOX", readonly=readonly)
    return mail


def close_imap(mail: Optional[imaplib.IMAP4_SSL]) -> None:
    if mail is None:
        return
    try:
        mail.close()
    except Exception:
        pass
    try:
        mail.logout()
    except Exception:
        pass


def find_junk_folder(mail: imaplib.IMAP4_SSL, provider: str) -> str:
    """
    Locate the server's Junk/Spam folder.

    Hardcoding "[Gmail]/Spam" breaks for non-English accounts, where the
    folder is named "[Gmail]/Spam" only in English locales. RFC 6154
    special-use flags are locale-independent, so we read those first.
    """
    try:
        typ, data = mail.list()
        if typ == "OK" and data:
            for raw in data:
                line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
                if "\\Junk" in line or "\\Spam" in line:
                    quoted = re.findall(r'"([^"]*)"', line)
                    if quoted:
                        return quoted[-1]
                    return line.split()[-1]
    except Exception:
        pass

    return FALLBACK_JUNK_FOLDERS.get(provider, "Junk")


# =========================================================
# MESSAGE PARSING
# =========================================================

def parse_message(raw_bytes: bytes, uid: str, provider: str) -> Dict[str, Any]:
    """Turn raw RFC822 bytes into a SafeApply email document."""
    msg = email_pkg.message_from_bytes(raw_bytes)

    subject = _decode_mime_header(msg.get("Subject", "")) or "(no subject)"
    from_header = _decode_mime_header(msg.get("From", "")) or "Unknown Sender"
    date_str = msg.get("Date", "")
    message_id = (msg.get("Message-ID", "") or "").strip()
    body = _extract_body_from_email_message(msg)

    match = re.search(r"<([^>]+)>", from_header)
    sender_email = match.group(1).strip() if match else from_header.strip()
    sender_name = from_header.replace(f"<{sender_email}>", "").strip().strip('"') or sender_email

    is_rec = is_recruitment_email(subject, body, sender_email)

    return {
        "id": make_email_doc_id(message_id, sender_email, subject, date_str),
        "message_id": message_id,
        "imap_uid": str(uid),
        "provider": provider,
        "sender": sender_email,
        "sender_name": sender_name,
        "subject": subject,
        "date": str(date_str)[:40] or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "body": body,
        "is_recruitment": is_rec,
        "status": "unscanned",
        "folder": "inbox",
        "mailbox_action": "none",
        "user_decision": "none",
        "company_name": "Unknown",
        "role_title": "Not Specified",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# =========================================================
# SYNC
# =========================================================

def sync_mailbox_to_db(
    max_messages: int = 25,
    scan_window: int = 120,
    user_id: str = DEFAULT_USER_ID,
    credentials: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fetch recent INBOX messages, keep the recruitment-related ones, and
    persist them to Cosmos.

    Args:
        max_messages: stop after storing this many recruitment emails.
        scan_window:  how many of the most recent messages to inspect. Most
                      inboxes are mostly non-recruitment mail, so the window
                      must be considerably larger than max_messages.

    Returns a summary dict for the UI / worker log.
    """
    creds = credentials or get_mail_credentials()

    if not creds["username"] or not creds["password"]:
        return {
            "ok": False,
            "error": "Mailbox credentials are not set. Add MAIL_USERNAME and "
                     "MAIL_APP_PASSWORD to your .env file.",
            "inspected": 0, "recruitment": 0, "stored": 0, "skipped": 0,
        }

    mail = None
    inspected = recruitment = skipped = 0
    to_store: List[Dict[str, Any]] = []

    try:
        mail = open_imap(
            provider=creds["provider"],
            username=creds["username"],
            password=creds["password"],
            server=creds.get("server"),
            port=creds.get("port", 993),
            readonly=True,
        )

        typ, data = mail.uid("SEARCH", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return {"ok": True, "inspected": 0, "recruitment": 0, "stored": 0,
                    "skipped": 0, "error": ""}

        uids = data[0].split()
        window = uids[-min(len(uids), scan_window):]
        window.reverse()  # newest first

        for uid_bytes in window:
            if len(to_store) >= max_messages:
                break

            uid = uid_bytes.decode() if isinstance(uid_bytes, bytes) else str(uid_bytes)
            inspected += 1

            try:
                typ, msg_data = mail.uid("FETCH", uid, "(RFC822)")
                if typ != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw = msg_data[0][1]
                if not isinstance(raw, (bytes, bytearray)):
                    continue

                doc = parse_message(bytes(raw), uid, creds["provider"])

                # Only recruitment mail is ever written to Azure. Everything
                # else is discarded here and never leaves the user's mailbox.
                if not doc["is_recruitment"]:
                    skipped += 1
                    continue

                recruitment += 1
                to_store.append(doc)

            except Exception as exc:  # noqa: BLE001
                print(f"[mail_sync] could not read UID {uid}: {exc}")
                continue

        stored = db_save_emails(to_store, user_id=user_id) if to_store else 0

        db_set_state(
            "last_sync",
            {
                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "inspected": inspected,
                "recruitment": recruitment,
                "stored": stored,
            },
            user_id=user_id,
        )

        return {
            "ok": True, "inspected": inspected, "recruitment": recruitment,
            "stored": stored, "skipped": skipped, "error": "",
        }

    except ConnectionError as exc:
        return {"ok": False, "error": str(exc), "inspected": inspected,
                "recruitment": recruitment, "stored": 0, "skipped": skipped}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Unexpected sync error: {exc}",
                "inspected": inspected, "recruitment": recruitment,
                "stored": 0, "skipped": skipped}
    finally:
        close_imap(mail)


if __name__ == "__main__":
    print("Mailbox configured:", is_mail_configured())
    print(sync_mailbox_to_db(max_messages=10, scan_window=60))