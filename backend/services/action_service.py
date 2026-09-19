"""
Action service for spam routing, restoration, and cryptographic audit logging.
"""

from typing import Any, Dict, List
from backend.errors import NotFoundError
from backend.schemas.mailbox import RestoreActionResponse, SpamActionResponse
from backend.schemas.audit import AuditChainStatusResponse, AuditRecordSchema
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.mail_provider import MailProviderAdapter


class ActionService:
    @staticmethod
    def move_to_spam(email_id: str, reason: str, user_id: str) -> SpamActionResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        res = MailProviderAdapter.move_to_spam(email_id=email_id, reason=reason, user_id=user_id, automated=False)

        audits = RepositoryAdapter.fetch_audit(user_id)
        last_audit_id = audits[-1]["id"] if audits else None

        return SpamActionResponse(
            ok=res.get("ok", True),
            mailbox_moved=res.get("mailbox_moved", False),
            local_quarantined=True,
            error=res.get("error"),
            audit_id=last_audit_id,
        )

    @staticmethod
    def restore_from_spam(email_id: str, user_id: str) -> RestoreActionResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        res = MailProviderAdapter.restore_from_spam(email_id=email_id, user_id=user_id)

        audits = RepositoryAdapter.fetch_audit(user_id)
        last_audit_id = audits[-1]["id"] if audits else None

        return RestoreActionResponse(
            ok=res.get("ok", True),
            mailbox_restored=res.get("mailbox_restored", False),
            error=res.get("error"),
            audit_id=last_audit_id,
        )

    @staticmethod
    def get_audit_trail(user_id: str) -> List[AuditRecordSchema]:
        records = RepositoryAdapter.fetch_audit(user_id)
        return [
            AuditRecordSchema(
                id=r["id"],
                sequence=r.get("sequence", 0),
                action=r.get("action", "unknown"),
                email_doc_id=r.get("email_doc_id"),
                timestamp=r.get("timestamp", ""),
                details=r.get("details", {}),
                prev_hash=r.get("prev_hash", ""),
                record_hash=r.get("record_hash", ""),
            )
            for r in reversed(records)
        ]

    @staticmethod
    def verify_audit_chain(user_id: str) -> AuditChainStatusResponse:
        chain = RepositoryAdapter.verify_audit_chain(user_id)
        return AuditChainStatusResponse(
            valid=chain.get("valid", True),
            records=chain.get("records", 0),
            broken_at=chain.get("broken_at"),
            reason=chain.get("reason"),
        )
