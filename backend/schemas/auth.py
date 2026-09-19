"""
Session and anonymous visitor schemas.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class SessionPrincipal(BaseModel):
    session_id: str
    created_at: str
    is_new: bool = False
    full_name: Optional[str] = "Anonymous Candidate"

    @property
    def user_id(self) -> str:
        """Alias for database partition key compatibility."""
        return self.session_id

    @property
    def email(self) -> str:
        return f"{self.session_id}@anonymous.safeapply.local"

    @property
    def role(self) -> str:
        return "anonymous_candidate"


# Backwards compatibility alias for components importing UserPrincipal
UserPrincipal = SessionPrincipal


class SessionStatusResponse(BaseModel):
    session_id: str
    created_at: str
    expires_at: Optional[str] = None
    has_profile: bool = False
    has_resume: bool = False
    has_mailbox: bool = False
    storage_mode: str = "anonymous_session_isolated"


class DataPurgeResponse(BaseModel):
    success: bool = True
    message: str = "All personal data, resumes, emails, and audit logs permanently deleted."
    purged_items: Dict[str, int] = Field(default_factory=dict)
