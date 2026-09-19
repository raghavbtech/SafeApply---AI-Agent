"""
FastAPI Dependencies: Authentication and Principal resolution.
"""

from typing import Optional
from fastapi import Depends, Header, Cookie, Request
from backend.config import settings
from backend.errors import UnauthorizedError
from backend.schemas.auth import UserPrincipal
from backend.security.identity import decode_access_token


async def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    safeapply_session: Optional[str] = Cookie(None),
) -> UserPrincipal:
    """
    Extract and validate the authenticated user principal from Bearer token or session cookie.
    In development mode, if no token is provided, safely resolves to the configured default demo user.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :].strip()
    elif safeapply_session:
        token = safeapply_session.strip()

    if token:
        principal = decode_access_token(token)
        if principal:
            return principal
        raise UnauthorizedError("Invalid or expired session token.")

    # Development convenience fallback: allow demo user if in development environment
    if settings.environment == "development":
        return UserPrincipal(
            user_id=settings.default_user_id,
            email=settings.default_user_id,
            full_name="Aarav Sharma (Demo Candidate)",
            role="candidate",
        )

    raise UnauthorizedError("Authentication required. Please sign in.")


async def get_optional_user(
    authorization: Optional[str] = Header(None),
    safeapply_session: Optional[str] = Cookie(None),
) -> Optional[UserPrincipal]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer ") :].strip()
    elif safeapply_session:
        token = safeapply_session.strip()

    if token:
        return decode_access_token(token)
    return None
