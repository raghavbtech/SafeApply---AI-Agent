"""
Session token creation and verification utilities.
Replaces obsolete password hashing with cryptographic session token helpers.
"""

import hashlib
import secrets
from typing import Optional
from backend.security.session import SessionStore, SessionPrincipal, hash_token


def create_session_for_test(session_id: Optional[str] = None) -> tuple[SessionPrincipal, str]:
    """Helper for automated test fixtures to obtain a valid session and raw token."""
    principal, raw_token = SessionStore.create_session(user_agent="pytest-client")
    return principal, raw_token
