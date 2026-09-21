"""
Mail provider adapter wrapping IMAP sync, spam move, restore, and MIME parsing.
Guarantees per-session mailbox credentials and isolation.
"""

import base64
import hashlib
import os
from typing import Any, Dict, Optional
from datetime import datetime, timezone

try:
    from cryptography.fernet import Fernet  # type: ignore
except ImportError:
    Fernet = None  # type: ignore

import mail_sync
import auto_scan
import mail_agent
import azure_db
from backend.config import settings


def _get_encryption_key() -> bytes:
    return hashlib.sha256(settings.session_secret.encode("utf-8")).digest()


def encrypt_credential(plain_text: str) -> str:
    if not plain_text:
        return ""
    if Fernet is not None:
        try:
            key = base64.urlsafe_b64encode(_get_encryption_key())
            f = Fernet(key)
            return f.encrypt(plain_text.encode("utf-8")).decode("utf-8")
        except Exception:
            pass

    # Reversible authenticated XOR stream fallback
    iv = os.urandom(16)
    key = _get_encryption_key()
    keystream = hashlib.sha256(key + iv).digest()
    plain_bytes = plain_text.encode("utf-8")
    while len(keystream) < len(plain_bytes):
        keystream += hashlib.sha256(key + keystream).digest()
    cipher = bytes(p ^ k for p, k in zip(plain_bytes, keystream))
    mac = hashlib.sha256(key + iv + cipher).digest()[:8]
    return "enc:" + base64.b64encode(iv + mac + cipher).decode("utf-8")


def decrypt_credential(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    if Fernet is not None and not cipher_text.startswith("enc:"):
        try:
            key = base64.urlsafe_b64encode(_get_encryption_key())
            f = Fernet(key)
            return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
        except Exception:
            pass

    if cipher_text.startswith("enc:"):
        try:
            raw = base64.b64decode(cipher_text[4:].encode("utf-8"))
            iv, mac, cipher = raw[:16], raw[16:24], raw[24:]
            key = _get_encryption_key()
            expected_mac = hashlib.sha256(key + iv + cipher).digest()[:8]
            if mac != expected_mac:
                return ""
            keystream = hashlib.sha256(key + iv).digest()
            while len(keystream) < len(cipher):
                keystream += hashlib.sha256(key + keystream).digest()
            plain_bytes = bytes(c ^ k for c, k in zip(cipher, keystream))
            return plain_bytes.decode("utf-8")
        except Exception:
            return ""

    return cipher_text


class MailProviderAdapter:
    @staticmethod
    def is_configured(user_id: Optional[str] = None) -> bool:
        """
        Check if mailbox has active credentials.
        """
        info = MailProviderAdapter.get_connection_info(user_id=user_id)
        return bool(info.get("is_connected"))

    @staticmethod
    def get_connection_info(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check mailbox connection for this specific visitor session.
        Never returns raw or encrypted passwords to the frontend or API callers.
        """
        effective_uid = user_id or settings.safeapply_user_id or azure_db.DEFAULT_USER_ID
        if effective_uid:
            auth = azure_db.db_get_state("mailbox_auth", default=None, user_id=effective_uid)
            if auth and isinstance(auth, dict):
                if auth.get("is_connected"):
                    return {
                        "provider": auth.get("provider", "Gmail"),
                        "username": auth.get("username", ""),
                        "is_connected": True,
                        "status": "connected",
                        "imap_server": auth.get("imap_server", "imap.gmail.com"),
                        "imap_port": auth.get("imap_port", 993),
                        "last_sync": auth.get("last_sync"),
                        "stored_count": len(azure_db.db_fetch_all_emails(user_id=effective_uid)),
                    }
                elif auth.get("is_connected") is False:
                    # User explicitly disconnected
                    return {
                        "provider": "None",
                        "username": "",
                        "is_connected": False,
                        "status": "disconnected",
                        "imap_server": "",
                        "imap_port": 993,
                        "last_sync": None,
                        "stored_count": len(azure_db.db_fetch_all_emails(user_id=effective_uid)),
                    }

        # Check .env configured credentials fallback ONLY for the default admin user
        is_default_admin = (not user_id) or (user_id == settings.safeapply_user_id) or (user_id == azure_db.DEFAULT_USER_ID)
        if is_default_admin and settings.environment != "testing" and settings.mail_username and settings.mail_app_password:
            stored_count = len(azure_db.db_fetch_all_emails(user_id=effective_uid)) if effective_uid else 0
            return {
                "provider": settings.mail_provider or "Gmail",
                "username": settings.mail_username,
                "is_connected": True,
                "status": "connected",
                "imap_server": settings.mail_imap_server or "imap.gmail.com",
                "imap_port": settings.mail_imap_port or 993,
                "last_sync": None,
                "stored_count": stored_count,
            }

        # If not connected by user or .env
        stored_count = len(azure_db.db_fetch_all_emails(user_id=effective_uid)) if effective_uid else 0
        return {
            "provider": "None",
            "username": "",
            "is_connected": False,
            "status": "disconnected",
            "imap_server": "",
            "imap_port": 993,
            "last_sync": None,
            "stored_count": stored_count,
        }

    @staticmethod
    def connect_mailbox(user_id: str, creds: Dict[str, Any]) -> Dict[str, Any]:
        """Save per-session mailbox authorization with encrypted credentials."""
        raw_token = creds.get("password_or_app_token", "")
        encrypted_token = encrypt_credential(raw_token)
        state = {
            "provider": creds.get("provider", "Gmail"),
            "username": creds.get("username", ""),
            "encrypted_password_or_token": encrypted_token,
            "imap_server": creds.get("imap_server") or "imap.gmail.com",
            "imap_port": creds.get("imap_port", 993),
            "is_connected": True,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_sync": None,
        }
        azure_db.db_set_state("mailbox_auth", state, user_id=user_id)
        return MailProviderAdapter.get_connection_info(user_id)

    @staticmethod
    def get_decrypted_credentials(user_id: str) -> Optional[Dict[str, Any]]:
        """Internal helper for background workers to retrieve decrypted credentials."""
        auth = azure_db.db_get_state("mailbox_auth", default=None, user_id=user_id)
        if not auth or not isinstance(auth, dict) or not auth.get("is_connected"):
            # Fallback to .env for the default admin user
            is_default_admin = (not user_id) or (user_id == settings.safeapply_user_id) or (user_id == azure_db.DEFAULT_USER_ID)
            if is_default_admin and settings.environment != "testing" and settings.mail_username and settings.mail_app_password:
                return {
                    "provider": settings.mail_provider or "Gmail",
                    "username": settings.mail_username,
                    "password_or_token": settings.mail_app_password,
                    "imap_server": settings.mail_imap_server or "imap.gmail.com",
                    "imap_port": settings.mail_imap_port or 993,
                }
            return None
        enc = auth.get("encrypted_password_or_token") or auth.get("password_or_token", "")
        token = decrypt_credential(enc)
        return {
            "provider": auth.get("provider", "Gmail"),
            "username": auth.get("username", ""),
            "password_or_token": token,
            "imap_server": auth.get("imap_server", "imap.gmail.com"),
            "imap_port": auth.get("imap_port", 993),
        }

    @staticmethod
    def disconnect_mailbox(user_id: str) -> bool:
        """Disconnect and delete stored credentials for this session."""
        azure_db.db_set_state(
            "mailbox_auth",
            {"is_connected": False, "disconnected_at": datetime.now(timezone.utc).isoformat()},
            user_id=user_id,
        )
        return True

    @staticmethod
    def sync_mailbox(user_id: str, max_messages: int = 15) -> Dict[str, Any]:
        creds = MailProviderAdapter.get_decrypted_credentials(user_id)
        res = mail_sync.sync_mailbox_to_db(max_messages=max_messages, user_id=user_id, credentials=creds)
        if "new_stored" not in res and "stored" in res:
            res["new_stored"] = res["stored"]
        return res

    @staticmethod
    def move_to_spam(email_id: str, reason: str, user_id: str, automated: bool = False) -> Dict[str, Any]:
        return auto_scan.move_to_spam(doc_id=email_id, reason=reason, user_id=user_id, automated=automated)

    @staticmethod
    def restore_from_spam(email_id: str, user_id: str) -> Dict[str, Any]:
        return auto_scan.restore_from_spam(doc_id=email_id, user_id=user_id)

    @staticmethod
    def parse_eml_bytes(content: bytes) -> Dict[str, Any]:
        """Parse raw MIME .eml file and convert to normalized email dictionary."""
        parsed = mail_agent.parse_eml_content(content)
        if not parsed.get("id"):
            parsed["id"] = mail_sync.make_email_doc_id(
                parsed.get("message_id", ""),
                parsed.get("sender", ""),
                parsed.get("subject", ""),
                parsed.get("date", ""),
            )
        return parsed
