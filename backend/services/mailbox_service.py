"""
Mailbox management, email listing, and inbox ingestion service.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.errors import NotFoundError, ValidationError
from backend.schemas.emails import EmailDetailResponse, EmailListItem, EmlImportResponse
from backend.schemas.mailbox import MailboxConnectionStatus, SyncMailboxResult, BatchScanResult
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.mail_provider import MailProviderAdapter
from backend.adapters.security_engine import SecurityEngineAdapter
import auto_scan


class MailboxService:
    @staticmethod
    def list_emails(
        user_id: str,
        folder: Optional[str] = "inbox",
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        raw_emails = RepositoryAdapter.fetch_all_emails(user_id=user_id, folder=folder, status=status)

        # In-memory filtering for risk_level & search
        filtered = []
        for em in raw_emails:
            if risk_level and em.get("risk_level") != risk_level:
                continue
            if search:
                term = search.lower()
                subj = (em.get("subject") or "").lower()
                sender = (em.get("sender") or "").lower()
                comp = (em.get("company_name") or "").lower()
                if term not in subj and term not in sender and term not in comp:
                    continue
            filtered.append(em)

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        items = [
            EmailListItem(
                id=em["id"],
                message_id=em.get("message_id"),
                imap_uid=str(em.get("imap_uid")) if em.get("imap_uid") else None,
                sender=em.get("sender", "unknown"),
                sender_name=em.get("sender_name"),
                subject=em.get("subject", "(no subject)"),
                date=em.get("date"),
                company_name=em.get("company_name", "Unknown"),
                role_title=em.get("role_title", "Not Specified"),
                status=em.get("status", "unscanned"),
                folder=em.get("folder", "inbox"),
                mailbox_action=em.get("mailbox_action", "none"),
                user_decision=em.get("user_decision", "none"),
                is_recruitment=em.get("is_recruitment", True),
                risk_score=em.get("risk_score"),
                risk_level=em.get("risk_level"),
                quarantined_at=em.get("quarantined_at"),
                quarantine_reason=em.get("quarantine_reason"),
                quarantined_automatically=em.get("quarantined_automatically", False),
                applied_at=em.get("applied_at"),
                synced_at=em.get("synced_at"),
            )
            for em in paginated
        ]

        return {
            "items": items,
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total,
            },
        }

    @staticmethod
    def get_email(email_id: str, user_id: str) -> EmailDetailResponse:
        em = RepositoryAdapter.fetch_email(email_id, user_id)
        if not em:
            raise NotFoundError(resource="Email", identifier=email_id)

        return EmailDetailResponse(
            id=em["id"],
            message_id=em.get("message_id"),
            imap_uid=str(em.get("imap_uid")) if em.get("imap_uid") else None,
            sender=em.get("sender", "unknown"),
            sender_name=em.get("sender_name"),
            subject=em.get("subject", "(no subject)"),
            date=em.get("date"),
            company_name=em.get("company_name", "Unknown"),
            role_title=em.get("role_title", "Not Specified"),
            status=em.get("status", "unscanned"),
            folder=em.get("folder", "inbox"),
            mailbox_action=em.get("mailbox_action", "none"),
            user_decision=em.get("user_decision", "none"),
            is_recruitment=em.get("is_recruitment", True),
            risk_score=em.get("risk_score"),
            risk_level=em.get("risk_level"),
            quarantined_at=em.get("quarantined_at"),
            quarantine_reason=em.get("quarantine_reason"),
            quarantined_automatically=em.get("quarantined_automatically", False),
            applied_at=em.get("applied_at"),
            synced_at=em.get("synced_at"),
            body=em.get("body", ""),
            analysis=em.get("analysis"),
            original_risk_score=em.get("original_risk_score"),
            original_risk_level=em.get("original_risk_level"),
            user_override=em.get("user_override"),
            application_package=em.get("application_package"),
            submission_id=em.get("submission_id"),
        )

    @staticmethod
    def import_eml(content_bytes: bytes, user_id: str) -> EmlImportResponse:
        if not content_bytes or len(content_bytes) < 10:
            raise ValidationError("Uploaded EML file is empty or corrupted.")

        parsed = MailProviderAdapter.parse_eml_bytes(content_bytes)
        # Store in user repository
        RepositoryAdapter.save_emails([parsed], user_id=user_id)

        # Write audit event
        RepositoryAdapter.write_audit(
            action="import_eml",
            email_id=parsed["id"],
            details={
                "subject": parsed.get("subject"),
                "sender": parsed.get("sender"),
                "is_recruitment": parsed.get("is_recruitment", False),
            },
            user_id=user_id,
        )

        body = parsed.get("body", "")
        return EmlImportResponse(
            id=parsed["id"],
            is_recruitment=parsed.get("is_recruitment", False),
            subject=parsed.get("subject", ""),
            sender=parsed.get("sender", ""),
            sender_name=parsed.get("sender_name"),
            date=parsed.get("date"),
            company_name=parsed.get("company_name"),
            role_title=parsed.get("role_title"),
            body_snippet=body[:200] + ("..." if len(body) > 200 else ""),
            status=parsed.get("status", "unscanned"),
        )

    @staticmethod
    def get_dashboard(user_id: str) -> Dict[str, Any]:
        stats = RepositoryAdapter.get_mailbox_stats(user_id)
        conn_info = MailProviderAdapter.get_connection_info()
        service_health = SecurityEngineAdapter.get_service_health()
        chain = RepositoryAdapter.verify_audit_chain(user_id)
        applied_jobs = RepositoryAdapter.get_applied_jobs(user_id)

        return {
            "stats": stats,
            "connection": conn_info,
            "service_health": service_health,
            "storage_backend": RepositoryAdapter.get_storage_backend(),
            "audit_chain": chain,
            "total_applications": len(applied_jobs),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def sync_mailbox(user_id: str, max_messages: int = 15) -> SyncMailboxResult:
        res = MailProviderAdapter.sync_mailbox(user_id=user_id, max_messages=max_messages)
        return SyncMailboxResult(
            ok=res.get("ok", False),
            inspected=res.get("inspected", 0),
            recruitment=res.get("recruitment", 0),
            skipped=res.get("skipped", 0),
            new_stored=res.get("new_stored", 0),
            error=res.get("error"),
            synced_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def batch_scan_unscanned(user_id: str, limit: int = 50) -> BatchScanResult:
        # Check user automation preferences
        prefs = RepositoryAdapter.get_preferences(user_id)
        allow_quarantine = prefs.get("auto_quarantine_enabled", False)
        allow_auto_apply = prefs.get("auto_apply_enabled", False)

        unscanned_before = RepositoryAdapter.fetch_all_emails(user_id=user_id, status="unscanned")
        results = auto_scan.scan_all_unscanned(
            user_id=user_id,
            limit=limit,
            allow_auto_quarantine=allow_quarantine,
            allow_auto_apply=allow_auto_apply,
        )

        quarantined = sum(1 for r in results if r.get("quarantined"))
        applied = sum(1 for r in results if r.get("applied"))

        return BatchScanResult(
            total_unscanned=len(unscanned_before),
            scanned_count=len(results),
            quarantined_count=quarantined,
            applied_count=applied,
            results=results,
        )
