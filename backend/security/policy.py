"""
Security policies and ownership verification.
Ensures no cross-user data access (IDOR prevention).
"""

from typing import Any, Dict, Optional
from backend.errors import ForbiddenError, NotFoundError
from backend.schemas.auth import UserPrincipal


def enforce_email_ownership(email_doc: Optional[Dict[str, Any]], principal: UserPrincipal) -> Dict[str, Any]:
    """Verify that an email document belongs to the authenticated user."""
    if not email_doc:
        raise NotFoundError(resource="Email", identifier="specified_id")
    
    owner = email_doc.get("user_id")
    if owner and owner != principal.user_id:
        raise ForbiddenError("You do not have permission to access this email.")
    
    return email_doc


def enforce_job_ownership(job_doc: Optional[Dict[str, Any]], principal: UserPrincipal) -> Dict[str, Any]:
    """Verify that an application record belongs to the authenticated user."""
    if not job_doc:
        raise NotFoundError(resource="Application", identifier="specified_id")
    
    owner = job_doc.get("user_id")
    if owner and owner != principal.user_id:
        raise ForbiddenError("You do not have permission to access this application.")
    
    return job_doc
