"""
Anonymous session management and data deletion endpoints.
Zero accounts, zero passwords, instant data purge.
"""

from fastapi import APIRouter, Depends, Response
from backend.config import settings
from backend.schemas.auth import SessionPrincipal, SessionStatusResponse, DataPurgeResponse
from backend.security.session import SessionStore
from backend.dependencies import get_current_session
from backend.adapters.repository import RepositoryAdapter
from backend.services.profile_service import ProfileService
import azure_db

router = APIRouter(prefix="/session", tags=["Session"])


@router.get("", response_model=SessionStatusResponse)
async def get_session_status(
    current_session: SessionPrincipal = Depends(get_current_session),
):
    """
    Get current anonymous visitor session status, expiration, and onboarding flags.
    Automatically initializes a fresh session if client doesn't have one.
    """
    prof = RepositoryAdapter.get_candidate_profile(current_session.user_id)
    has_profile = bool(prof and prof.get("full_name") and len(prof.get("skills", [])) >= 1)
    has_resume = bool(prof and prof.get("resume_filename"))

    # Check mailbox connection for this session
    mailbox_auth = azure_db.db_get_state("mailbox_auth", default=None, user_id=current_session.user_id)
    has_mailbox = bool(mailbox_auth and mailbox_auth.get("is_connected"))

    session_rec = SessionStore.get_session_info(current_session.session_id)
    expires_at = session_rec.expires_at if session_rec else None

    return SessionStatusResponse(
        session_id=current_session.session_id,
        created_at=current_session.created_at,
        expires_at=expires_at,
        has_profile=has_profile,
        has_resume=has_resume,
        has_mailbox=has_mailbox,
        storage_mode="anonymous_session_isolated",
    )


@router.delete("/data", response_model=DataPurgeResponse)
@router.post("/purge", response_model=DataPurgeResponse)
async def purge_session_data(
    response: Response,
    current_session: SessionPrincipal = Depends(get_current_session),
):
    """
    'Delete My Data': Permanently erase all emails, candidate profile, uploaded resume file,
    and cryptographic audit records associated with this visitor session. Clears session cookie.
    """
    session_id = current_session.session_id

    # 1. Delete resume file from private storage
    ProfileService.delete_resume(session_id)

    # 2. Purge all partitioned records in database / local fallback
    purged_counts = RepositoryAdapter.purge_user_data(session_id)

    # 3. Revoke session in server store
    SessionStore.delete_session(session_id)

    # 4. Clear HTTP-only session cookie
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )

    return DataPurgeResponse(
        success=True,
        message="All personal data, resumes, emails, and audit logs permanently deleted.",
        purged_items=purged_counts,
    )
