"""
FastAPI Dependencies: Anonymous Visitor Session and Principal resolution.
Zero accounts, zero passwords, automatic cookie issuance.
"""

from typing import Optional
from fastapi import Header, Request, Response
from backend.config import settings
from backend.schemas.auth import SessionPrincipal
from backend.security.session import SessionStore


async def get_current_session(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None),
) -> SessionPrincipal:
    """
    Resolve visitor's private session from HTTP-only cookie or Bearer token.
    If missing, expired, or invalid, automatically issues a brand-new cryptographically
    secure anonymous session and attaches the Set-Cookie header.
    """
    raw_token = None

    # Check Authorization header (for test suites, scripts, or non-browser clients)
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization[len("Bearer ") :].strip()

    # Check HTTP-only session cookie
    if not raw_token:
        cookie_val = request.cookies.get(settings.cookie_name)
        if cookie_val:
            raw_token = cookie_val.strip()

    # If token present, validate against server-side token hash
    if raw_token:
        principal = SessionStore.validate_session(raw_token)
        if principal:
            return principal

    # Missing, expired, or tampered token: issue brand-new anonymous session
    principal, new_raw_token = SessionStore.create_session(
        user_agent=request.headers.get("user-agent")
    )

    # Set secure HTTP-only session cookie
    response.set_cookie(
        key=settings.cookie_name,
        value=new_raw_token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        max_age=settings.session_expire_days * 86400,
        path="/",
    )

    return principal


# Backwards compatibility alias
get_current_user = get_current_session
