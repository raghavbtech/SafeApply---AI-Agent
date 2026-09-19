"""
Repository adapter wrapping azure_db.py with strict user scoping.
"""

from typing import Any, Dict, List, Optional
import azure_db
import job_agent
from backend.schemas.profile import CandidateProfileSchema
from backend.schemas.preferences import UserPreferencesSchema


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
        """User-scoped profile from persistent state, falling back to legacy profile file."""
        stored = azure_db.db_get_state("candidate_profile", default=None, user_id=user_id)
        if stored and isinstance(stored, dict) and stored.get("full_name"):
            return stored
        # Fallback to local profile loader
        legacy = job_agent.load_candidate_profile()
        return legacy

    @staticmethod
    def save_candidate_profile(profile: Dict[str, Any], user_id: str) -> None:
        """Persist profile per-user in state, and update local file for backwards compatibility."""
        azure_db.db_set_state("candidate_profile", profile, user_id=user_id)
        try:
            job_agent.save_candidate_profile(profile)
        except Exception:
            pass

    @staticmethod
    def get_preferences(user_id: str) -> Dict[str, Any]:
        default_prefs = {
            "auto_quarantine_enabled": False,
            "auto_quarantine_threshold": 65,
            "auto_apply_enabled": False,
            "auto_apply_max_risk_score": 45,
            "enable_real_smtp_dispatch": False,
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
