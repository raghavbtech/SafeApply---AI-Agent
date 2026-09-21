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
import html
from datetime import datetime
from typing import List, Dict, Any, Optional

from agent import analyze_job_offer
from azure_db import (
    db_save_emails,
    db_fetch_all_emails,
    db_update_email_status,
    db_get_known_identifiers,
)


# =========================================================
# RECRUITMENT CLASSIFIER (TWO-STAGE ACCURACY FILTER - FLAW 12)
# =========================================================

STRONG_RECRUITMENT_PATTERNS = [
    r"\boffer of internship\b",
    r"\boffer letter\b",
    r"\binternship offer\b",
    r"\bjob offer\b",
    r"\bselection letter\b",
    r"\bselected as\b",
    r"\bappointment letter\b",
    r"\bletter of intent\b",
    r"\bhiring operations\b",
    r"\btalent acquisition\b",
    r"\brecruitment team\b",
    r"\binterview round\b",
    r"\binterview schedule\b",
    r"\btechnical interview\b",
    r"\bshortlisted for\b",
    r"\bplacement slot\b",
    r"\bctc\s*:\s*(?:inr|\u20b9|\$|rs\.?)\s*[\d,]+",
    r"\bstipend\s*:\s*(?:inr|\u20b9|\$|rs\.?)\s*[\d,]+",
    r"\bsalary\s*:\s*(?:inr|\u20b9|\$|rs\.?)\s*[\d,]+",
    r"\bcongratulations on your selection\b",
    r"\bwe are pleased to offer\b",
    r"\byou have been selected\b",
    r"\bwelcome to the team\b",
    r"\bjoining date\b",
    r"\bdate of joining\b",
    r"\bemployment agreement\b",
    r"\bemployment offer\b",
    r"\bdata entry specialist\b",
    r"\bwork from home \d+ hours\b",
    r"\bsoftware engineering intern\b",
    r"\bsystems engineer position\b",
    r"\bjob opportunity\b",
]

NON_RECRUITMENT_PATTERNS = [
    r"\bfinish setting up\b",
    r"\bsetting up your\b",
    r"\bgoogle account\b",
    r"\bwindows with google\b",
    r"\bsecurity alert\b",
    r"\bpassword reset\b",
    r"\bverification code\b",
    r"\bone-time password\b",
    r"\b2-step verification\b",
    r"\bdevice login\b",
    r"\bterms of service\b",
    r"\bprivacy policy\b",
    r"\border confirmation\b",
    r"\breceipt\b",
    r"\binvoice\b",
    r"\btracking number\b",
    r"\bshipment\b",
    r"\bnewsletter\b",
    r"\bdigest\b",
    r"\bunsubscribe\b",
    r"\bweekly update\b",
    r"\bdependabot\b",
    r"\bsecurity advisory\b",
    r"\bpromotional discount\b",
    r"\bbilling update\b",
    r"\bpayment successful\b",
    r"\bdelivery status notification\b",
    r"\bmailer-daemon\b",
    r"\btatacliq\b",
    r"\bpuma\b",
    r"\bdiscounts? louder than\b",
    r"\bshop now\b",
    r"\bflash sale\b",
    r"\bbig bash\b",
    r"\bcoupon\b",
    r"\bcart\b",
    r"\bcheckout\b",
    r"\bundeliverable\b",
    r"\breturned to sender\b",
    r"\bpostmaster\b",
    r"\bfailure notice\b",
]

RECRUITMENT_KEYWORDS = [
    r"\bjob\b", r"\boffer\b", r"\bintern\b", r"\binternship\b",
    r"\brecruit\b", r"\bhiring\b", r"\bselection\b", r"\bcandidat\b",
    r"\bstipend\b", r"\bsalary\b", r"\bctc\b", r"\blpa\b",
    r"\bcareer\b", r"\bplacement\b", r"\binterview\b", r"\bopening\b",
    r"\bposition\b", r"\bengineer\b", r"\bdeveloper\b", r"\bwork from home\b",
]


def is_recruitment_email(subject: str, body: str, sender: str = "") -> bool:
    """
    Two-stage recruitment email classifier (Flaw 12).
    Stage 1: Checks for definite non-recruitment indicators (account setup, security alerts, newsletters, receipts).
    Stage 2: Checks for strong and contextual recruitment indicators in subject, body, and sender.
    Strictly returns False for non-recruitment emails to ensure they are ignored.
    """
    subject_lower = (subject or "").lower()
    body_lower = (body or "").lower()
    sender_lower = (sender or "").lower()
    full_text = f"{subject_lower} {body_lower} {sender_lower}"

    # Prevent self-reply recursion: Never treat SafeApply's own automated application/response drafts as recruitment offers
    if "re: application & candidate profile" in subject_lower or "re: application for" in subject_lower:
        return False
    if "dear hiring team & talent acquisition" in body_lower or "i am very interested in this opportunity and would like to revert back" in body_lower:
        return False
    env_user = os.getenv("MAIL_USERNAME", "").strip().lower()
    if env_user and env_user in sender_lower:
        return False

    # Check strong recruitment patterns first (e.g. formal offer, selection letter, CTC)
    has_strong_recruitment = any(re.search(pat, full_text) for pat in STRONG_RECRUITMENT_PATTERNS)

    # Check non-recruitment patterns
    has_non_recruitment = any(re.search(pat, full_text) for pat in NON_RECRUITMENT_PATTERNS)

    # If it is a known non-recruitment type and lacks strong recruitment signals, immediately reject
    if has_non_recruitment and not has_strong_recruitment:
        return False

    if has_strong_recruitment:
        return True

    # Subject hits carry high intent weight (weight = 3)
    subject_hits = sum(1 for pat in RECRUITMENT_KEYWORDS if re.search(pat, subject_lower))
    body_hits = sum(1 for pat in RECRUITMENT_KEYWORDS if re.search(pat, body_lower))

    # Sender domain hint (recruiting, careers, hr, talent)
    sender_hit = any(k in sender_lower for k in ["recruiting", "career", "talent", "hr."])

    score = (subject_hits * 3) + body_hits + (2 if sender_hit else 0)

    # Require score of at least 2 for genuine recruitment classification
    threshold = 4 if has_non_recruitment else 2
    return score >= threshold


def is_header_definitely_non_recruitment(subject: str, sender: str) -> bool:
    """
    Fast pre-filter based strictly on Subject and Sender headers.
    Returns True ONLY for emails that are definitively non-recruitment (OTPs, shopping,
    delivery, bank alerts, subscriptions) AND contain zero recruitment signals.
    """
    sub_lower = (subject or "").lower()
    snd_lower = (sender or "").lower()
    text = f"{sub_lower} {snd_lower}"

    # Recruitment keywords - if ANY of these match, NEVER reject at header stage
    rec_patterns = [
        r"\bjob\b", r"\boffer\b", r"\bintern\b", r"\binternship\b",
        r"\brecruit", r"\bhiring\b", r"\bselection\b", r"\bcandidat",
        r"\bstipend\b", r"\bcareer", r"\bplacement\b", r"\binterview\b",
        r"\bopening\b", r"\bposition\b", r"\bengineer\b", r"\bdeveloper\b",
        r"\bshortlist", r"\bapplied\b", r"\bapplication\b", r"\bwork from home\b",
        r"\bglassdoor\b", r"\blinkedin\b", r"\bnaukri\b", r"\bindeed\b", r"\bunstop\b",
        r"\bwellfound\b", r"\bhirist\b", r"\binstahyre\b",
    ]
    if any(re.search(p, text) for p in rec_patterns):
        return False

    # Definite non-recruitment indicators
    non_rec_patterns = [
        r"\bwallet credit\b", r"\bcashback\b", r"\bdiscount\b", r"\bsale\b",
        r"\border placed\b", r"\border confirmation\b", r"\bdelivered\b",
        r"\btracking\b", r"\bshipment\b", r"\binvoice\b", r"\breceipt\b",
        r"\bverification code\b", r"\bone-time password\b", r"\botp\b",
        r"\bsecurity alert\b", r"\bsign-in\b", r"\bpassword reset\b",
        r"\bfinish setting up\b", r"\bbill due\b", r"\bstatement\b",
        r"\bnewsletter\b", r"\bweekly digest\b", r"\bunsubscribe\b",
        r"\bdependabot\b", r"\bpromotional discount\b", r"\bpayment successful\b",
        r"\bdelivery status notification\b", r"\bmailer-daemon\b", r"\bfailure\b",
        r"tatacliq\.com", r"puma\.com", r"swiggy\.in", r"zomato\.com", r"flipkart\.com",
        r"myntra\.com", r"uber\.com", r"ola\.com", r"netflix\.com",
    ]
    return any(re.search(p, text) for p in non_rec_patterns)


# =========================================================
# DEFAULT SIMULATED INBOX (EMPTY SCALED SCENE - ONLY LIVE IMAP / DB FETCHED EMAILS ARE USED)
# =========================================================

DEFAULT_DEMO_EMAILS: List[Dict[str, Any]] = []


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
            # Check if emails already exist in database
            stored = db_fetch_all_emails()
            self.emails = stored if stored else []

    def fetch_from_database(self) -> List[Dict[str, Any]]:
        """Instantaneously load pre-stored emails from the database into memory."""
        stored = db_fetch_all_emails()
        if stored:
            self.emails = stored
        return self.emails

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
        Ingest a new email into the mailbox and persist to database.
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
        try:
            db_save_emails([new_email])
        except Exception:
            pass
        return new_email

    def scan_single_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Run the full SafeApply multi-pillar pipeline on a specific email.
        Enriches analysis input with complete sender and subject metadata (Flaw 5).
        """
        email = self.get_email_by_id(email_id)
        if not email or not email.get("is_recruitment", True):
            return email

        email["status"] = "scanning"
        try:
            # Flaw 5: Include complete sender metadata and subject in the analyzed context
            full_context = (
                f"From: {email.get('sender_name', '')} <{email.get('sender', '')}>\n"
                f"Subject: {email.get('subject', '')}\n"
                f"Date: {email.get('date', '')}\n\n"
                f"{email.get('body', '')}"
            )

            analysis = analyze_job_offer(full_context)
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

            # Persist scanned result to database (Flaw 19)
            try:
                db_save_emails([email])
            except Exception:
                pass

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

    def ingest_live_emails(self, live_emails: List[Dict[str, Any]]) -> int:
        """Insert fetched live emails at the top of the mailbox and save to database (recruitment only)."""
        count = 0
        existing_ids = {e["id"] for e in self.emails}
        to_add = []
        for email_item in live_emails:
            # STRICT FILTER: ignore non-recruitment emails
            if not email_item.get("is_recruitment", False):
                continue
            if email_item["id"] not in existing_ids:
                self.emails.insert(0, email_item)
                to_add.append(email_item)
                count += 1

        if to_add:
            try:
                db_save_emails(to_add)
            except Exception:
                pass

        return count

    def update_email_status(self, email_id: str, new_status: str):
        """Update the status of an email (e.g., 'quarantined', 'applied') and persist."""
        email = self.get_email_by_id(email_id)
        if email:
            email["status"] = new_status
            try:
                db_update_email_status(email_id, new_status)
            except Exception:
                pass

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


# =========================================================
# LIVE IMAP & .EML MAIL CONNECTOR
# =========================================================

import imaplib
import email as email_pkg
import email.message
from email.header import decode_header


def _decode_mime_header(header_val: str) -> str:
    """Decode encoded MIME header fields."""
    if not header_val:
        return ""
    decoded_parts = decode_header(header_val)
    result = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(enc or "utf-8", errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def _extract_body_from_email_message(msg: email_pkg.message.Message) -> str:
    """Extract plain text or HTML body from python email Message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    break
            elif ctype == "text/html" and not body and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    raw_html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                    clean_html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
                    clean_text = re.sub(r"<[^>]+>", " ", clean_html)
                    body = html.unescape(clean_text)
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            raw_text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            if "<html" in raw_text.lower() or "<body" in raw_text.lower():
                clean_html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<[^>]+>", " ", clean_html)
                body = html.unescape(clean_text)
            else:
                body = html.unescape(raw_text)

    return re.sub(r"\s+", " ", body).strip()


def parse_eml_content(raw_bytes: bytes) -> Dict[str, Any]:
    """Parse an uploaded .eml file into a SafeApply email dictionary."""
    msg = email_pkg.message_from_bytes(raw_bytes)
    subject = _decode_mime_header(msg.get("Subject", "No Subject"))
    sender = _decode_mime_header(msg.get("From", "Unknown Sender"))
    date_str = msg.get("Date", datetime.now().strftime("%Y-%m-%d %I:%M %p"))
    body = _extract_body_from_email_message(msg)

    sender_match = re.search(r"<([^>]+)>", sender)
    sender_email = sender_match.group(1) if sender_match else sender
    sender_name = sender.replace(f"<{sender_email}>", "").strip() or sender_email

    is_rec = is_recruitment_email(subject, body, sender)

    return {
        "id": f"EML-UPLOAD-{datetime.now().strftime('%M%S')}",
        "sender": sender_email,
        "sender_name": sender_name,
        "subject": subject,
        "date": str(date_str)[:30],
        "body": body,
        "status": "unscanned" if is_rec else "ignored",
        "is_recruitment": is_rec,
        "company_name": "Unknown",
        "role_title": "Not Specified",
        "risk_score": None,
        "risk_level": None,
        "analysis": None,
    }


def fetch_live_emails(
    provider: str,
    username: str,
    password_or_app_token: str,
    max_emails: int = 10,
    server: Optional[str] = None,
    port: int = 993,
) -> List[Dict[str, Any]]:
    """
    Connect to Gmail, Outlook, or custom IMAP server via SSL and fetch recent emails.
    Includes input sanitization, connection timeouts, and helpful diagnostics.
    """
    import socket
    import time

    provider_servers = {
        "Gmail": ("imap.gmail.com", 993),
        "Outlook / Hotmail": ("outlook.office365.com", 993),
        "Yahoo": ("imap.mail.yahoo.com", 993),
    }

    provider_clean = (provider or "Gmail").strip()
    clean_user = (username or "").strip()
    clean_token = (password_or_app_token or "").strip()

    # For Gmail, Google App Passwords are generated with spaces (e.g. "abcd efgh ijkl mnop")
    if provider_clean == "Gmail":
        clean_token = clean_token.replace(" ", "")

    if server and server.strip():
        imap_host = server.strip()
        try:
            imap_port = int(port) if port else 993
        except ValueError:
            imap_port = 993
    else:
        imap_host, imap_port = provider_servers.get(provider_clean, ("imap.gmail.com", 993))
        imap_host = imap_host.strip()
        imap_port = int(imap_port)

    mail = None
    last_err = None

    # Attempt connection with timeout and retry
    for attempt in range(2):
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=15)
            break
        except socket.gaierror as ge:
            last_err = ge
            time.sleep(1)
        except (socket.timeout, TimeoutError) as te:
            last_err = te
            time.sleep(1)
        except Exception as e:
            last_err = e
            break

    if mail is None:
        if isinstance(last_err, socket.gaierror):
            raise ConnectionError(
                f"DNS resolution failed for '{imap_host}' ([Errno 11001] getaddrinfo failed). "
                f"Please verify that your device has an active internet connection and that the host address is correct."
            )
        elif isinstance(last_err, (socket.timeout, TimeoutError)):
            raise ConnectionError(
                f"Connection to '{imap_host}:{imap_port}' timed out after 15 seconds. "
                f"Please check your firewall or network connection."
            )
        else:
            raise ConnectionError(f"Could not connect to {imap_host}:{imap_port} - {last_err}")

    try:
        try:
            mail.login(clean_user, clean_token)
        except imaplib.IMAP4.error as auth_err:
            err_msg = str(auth_err)
            if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg or "login failed" in err_msg.lower():
                if provider_clean == "Gmail":
                    raise ConnectionError(
                        "Gmail Authentication Failed. Please check:\n"
                        "1. You must use a 16-letter Google App Password (not your personal Google account password).\n"
                        "2. 2-Step Verification must be enabled on your Google account.\n"
                        "3. In Gmail Settings > Forwarding and POP/IMAP, ensure 'Enable IMAP' is turned ON."
                    )
                else:
                    raise ConnectionError(
                        f"Authentication failed for {clean_user}. "
                        f"Please check your username and app password."
                    )
            raise ConnectionError(f"IMAP Error: {err_msg}")

        mail.select("INBOX", readonly=True)

        status, messages = mail.uid("SEARCH", None, "ALL")
        if status != "OK" or not messages[0]:
            return []

        all_uids = messages[0].split()
        window_size = min(len(all_uids), max(max_emails * 3, 40))
        recent_uids = all_uids[-window_size:]
        recent_uids.reverse()

        uid_strs = [u.decode() if isinstance(u, bytes) else str(u) for u in recent_uids]

        # Check known IDs in Cosmos DB to skip already-stored emails
        try:
            known_uids, known_msg_ids = db_get_known_identifiers()
        except Exception:
            known_uids, known_msg_ids = set(), set()

        # Tier 1: Fast batch header inspection
        candidate_uids = []
        chunk_size = 30
        for i in range(0, len(uid_strs), chunk_size):
            chunk = uid_strs[i:i + chunk_size]
            typ, res = mail.uid("FETCH", ",".join(chunk), "(UID BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID)])")
            if typ != "OK" or not res:
                continue

            for item in res:
                if isinstance(item, tuple) and len(item) > 1:
                    meta = item[0].decode(errors="replace") if isinstance(item[0], bytes) else str(item[0])
                    uid_match = re.search(r"UID\s+(\d+)", meta)
                    if not uid_match:
                        continue
                    uid = uid_match.group(1)

                    raw_hdr = item[1]
                    msg = email_pkg.message_from_bytes(raw_hdr) if isinstance(raw_hdr, bytes) else email_pkg.message_from_string(str(raw_hdr))
                    subj = _decode_mime_header(msg.get("Subject", ""))
                    sender = _decode_mime_header(msg.get("From", ""))
                    msg_id = (msg.get("Message-ID", "") or "").strip()

                    if uid in known_uids or (msg_id and msg_id in known_msg_ids):
                        continue
                    if is_header_definitely_non_recruitment(subj, sender):
                        continue

                    candidate_uids.append(uid)
                    if len(candidate_uids) >= max_emails * 2:
                        break

            if len(candidate_uids) >= max_emails * 2:
                break

        # Tier 2: Targeted batch fetch for candidate bodies
        fetched_emails = []
        if candidate_uids:
            c_chunk_size = 15
            for i in range(0, len(candidate_uids), c_chunk_size):
                if len(fetched_emails) >= max_emails:
                    break
                c_chunk = candidate_uids[i:i + c_chunk_size]
                typ, res = mail.uid("FETCH", ",".join(c_chunk), "(UID BODY.PEEK[])")
                if typ != "OK" or not res:
                    continue

                for item in res:
                    if isinstance(item, tuple) and len(item) > 1:
                        meta = item[0].decode(errors="replace") if isinstance(item[0], bytes) else str(item[0])
                        uid_match = re.search(r"UID\s+(\d+)", meta)
                        uid = uid_match.group(1) if uid_match else ""
                        raw_email = item[1]
                        if not isinstance(raw_email, (bytes, bytearray)):
                            continue

                        parsed = parse_eml_content(bytes(raw_email))
                        if not parsed.get("is_recruitment", False):
                            continue

                        parsed["id"] = f"LIVE-{uid}"
                        parsed["imap_uid"] = str(uid)
                        fetched_emails.append(parsed)
                        if len(fetched_emails) >= max_emails:
                            break

        # Automatically store fetched recruitment emails in database for instant access
        if fetched_emails:
            try:
                db_save_emails(fetched_emails)
            except Exception:
                pass

        return fetched_emails
    finally:
        try:
            mail.close()
            mail.logout()
        except Exception:
            pass
