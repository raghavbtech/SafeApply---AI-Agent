"""
Mail provider adapter wrapping IMAP sync, spam move, restore, and MIME parsing.
Guarantees per-session mailbox credentials and isolation.
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
import mail_sync
import auto_scan
import mail_agent
import azure_db
from backend.config import settings


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
        Falls back to global .env credentials only if user_id is the default demo user.
        """
        if user_id:
            auth = azure_db.db_get_state("mailbox_auth", default=None, user_id=user_id)
            if auth and isinstance(auth, dict) and auth.get("is_connected"):
                return {
                    "provider": auth.get("provider", "Gmail"),
                    "username": auth.get("username", ""),
                    "is_connected": True,
                    "status": "connected",
                    "imap_server": auth.get("imap_server", "imap.gmail.com"),
                    "imap_port": auth.get("imap_port", 993),
                    "last_sync": auth.get("last_sync"),
                    "stored_count": len(azure_db.db_fetch_all_emails(user_id=user_id)),
                }

        # If not connected by user
        stored_count = len(azure_db.db_fetch_all_emails(user_id=user_id)) if user_id else 0
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
        """Save per-session mailbox authorization."""
        state = {
            "provider": creds.get("provider", "Gmail"),
            "username": creds.get("username", ""),
            "password_or_token": creds.get("password_or_app_token", ""),
            "imap_server": creds.get("imap_server") or "imap.gmail.com",
            "imap_port": creds.get("imap_port", 993),
            "is_connected": True,
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_sync": None,
        }
        azure_db.db_set_state("mailbox_auth", state, user_id=user_id)
        return MailProviderAdapter.get_connection_info(user_id)

    @staticmethod
    def disconnect_mailbox(user_id: str) -> bool:
        """Disconnect and delete stored credentials for this session."""
        azure_db.db_set_state("mailbox_auth", {}, user_id=user_id)
        return True

    @staticmethod
    def sync_mailbox(user_id: str, max_messages: int = 15) -> Dict[str, Any]:
        return mail_sync.sync_mailbox_to_db(max_messages=max_messages, user_id=user_id)

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
