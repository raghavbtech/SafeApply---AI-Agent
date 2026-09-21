"""
Repository adapter wrapping azure_db.py with strict user scoping.
"""

from typing import Any, Dict, List, Optional
import azure_db
import job_agent
from backend.schemas.profile import CandidateProfileSchema
from backend.schemas.preferences import UserPreferencesSchema
from backend.config import settings


class RepositoryAdapter:
    """Provides user-scoped data persistence over Cosmos DB / Local JSON."""

    @staticmethod
    def fetch_all_emails(
        user_id: str,
        folder: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return azure_db.db_fetch_all_emails(user_id=user_id, folder=folder, status=status)

    @staticmethod
    def fetch_email(email_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        return azure_db.db_fetch_email(doc_id=email_id, user_id=user_id)

    @staticmethod
    def save_emails(emails: List[Dict[str, Any]], user_id: str) -> int:
        return azure_db.db_save_emails(emails=emails, user_id=user_id)

    @staticmethod
    def update_email(email_id: str, fields: Dict[str, Any], user_id: str) -> Optional[Dict[str, Any]]:
        return azure_db.db_update_email_fields(doc_id=email_id, fields=fields, user_id=user_id)

    @staticmethod
    def get_mailbox_stats(user_id: str) -> Dict[str, int]:
        return azure_db.db_mailbox_stats(user_id=user_id)

    @staticmethod
    def write_audit(action: str, email_id: str, details: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        return azure_db.db_write_audit(action=action, email_doc_id=email_id, details=details, user_id=user_id)

    @staticmethod
    def fetch_audit(user_id: str) -> List[Dict[str, Any]]:
        return azure_db.db_fetch_audit(user_id=user_id)

    @staticmethod
    def verify_audit_chain(user_id: str) -> Dict[str, Any]:
        return azure_db.db_verify_audit_chain(user_id=user_id)

    @staticmethod
    def save_applied_job(record: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        return azure_db.db_save_applied_job(record=record, user_id=user_id)

    @staticmethod
    def get_applied_jobs(user_id: str) -> List[Dict[str, Any]]:
        return azure_db.db_get_applied_jobs(user_id=user_id)

    @staticmethod
    def get_candidate_profile(user_id: str) -> Dict[str, Any]:
        """User-scoped profile from persistent state. Returns empty dict if not configured."""
        stored = azure_db.db_get_state("candidate_profile", default=None, user_id=user_id)
        if stored and isinstance(stored, dict) and any(stored.values()):
            return stored
        if user_id and settings.safeapply_user_id and user_id == settings.safeapply_user_id:
            import os, json
            prof_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "candidate_profile.json")
            if os.path.exists(prof_file):
                try:
                    with open(prof_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            return data
                except Exception:
                    pass
        return {}

    @staticmethod
    def save_candidate_profile(profile: Dict[str, Any], user_id: str) -> None:
        """Persist profile per visitor session in state."""
        azure_db.db_set_state("candidate_profile", profile, user_id=user_id)

    @staticmethod
    def delete_candidate_profile(user_id: str) -> None:
        """Erase candidate profile for this session."""
        azure_db.db_set_state("candidate_profile", {}, user_id=user_id)

    @staticmethod
    def purge_user_data(user_id: str) -> Dict[str, int]:
        """Purge all data (emails, audit, state, profile, resumes) for this user/session."""
        counts = azure_db.db_purge_user_data(user_id=user_id)
        from backend.adapters.blob_storage import BlobStorageAdapter
        resumes_purged = BlobStorageAdapter.purge_user_resumes(user_id=user_id)
        counts["resumes"] = resumes_purged
        return counts

    @staticmethod
    def get_preferences(user_id: str) -> Dict[str, Any]:
        default_prefs = {
            "auto_quarantine_enabled": settings.auto_quarantine_enabled,
            "auto_quarantine_threshold": settings.auto_quarantine_threshold,
            "auto_apply_enabled": settings.auto_apply_enabled,
            "auto_apply_max_risk_score": settings.auto_apply_max_risk_score,
            "enable_real_smtp_dispatch": settings.enable_real_smtp_dispatch,
        }
        stored = azure_db.db_get_state("user_preferences", default=default_prefs, user_id=user_id)
        if not isinstance(stored, dict):
            return default_prefs
        merged = dict(default_prefs)
        merged.update(stored)
        return merged

    @staticmethod
    def save_preferences(prefs: Dict[str, Any], user_id: str) -> None:
        azure_db.db_set_state("user_preferences", prefs, user_id=user_id)

    @staticmethod
    def get_storage_backend() -> str:
        return azure_db.storage_backend()
