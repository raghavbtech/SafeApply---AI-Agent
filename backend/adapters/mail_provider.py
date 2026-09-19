"""
Mail provider adapter wrapping IMAP sync, spam move, restore, and MIME parsing.
"""

from typing import Any, Dict, Optional
import mail_sync
import auto_scan
import mail_agent
from backend.config import settings


class MailProviderAdapter:
    @staticmethod
    def is_configured() -> bool:
        return mail_sync.is_mail_configured()

    @staticmethod
    def get_connection_info() -> Dict[str, Any]:
        creds = mail_sync.get_mail_credentials()
        is_conn = mail_sync.is_mail_configured()
        return {
            "provider": creds.get("provider", "Gmail"),
            "username": creds.get("username", ""),
            "is_connected": is_conn,
            "status": "connected" if is_conn else "disconnected",
            "imap_server": creds.get("server") or "imap.gmail.com",
            "imap_port": creds.get("port", 993),
        }

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
