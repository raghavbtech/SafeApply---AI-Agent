"""
CSRF Protection Middleware for Cookie-based requests.
Validates Origin / Referer on state-changing operations when browser session cookies are attached.
"""

from urllib.parse import urlparse
from fastapi import Request, status
from fastapi.responses import JSONResponse
from backend.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_protect_middleware(request: Request, call_next):
    if not settings.csrf_protection_enabled:
        return await call_next(request)

    # Safe HTTP methods don't mutate state
    if request.method in SAFE_METHODS:
        return await call_next(request)

    # Only enforce if request relies on the session cookie
    has_session_cookie = settings.cookie_name in request.cookies
    has_auth_header = bool(request.headers.get("authorization"))

    # If purely Authorization header is used, browser CSRF is not an attack vector
    if not has_session_cookie or has_auth_header:
        return await call_next(request)

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    candidate_origin = origin
    if not candidate_origin and referer:
        parsed = urlparse(referer)
        candidate_origin = f"{parsed.scheme}://{parsed.netloc}"

    # In development or tests without origin header (direct programmatic clients)
    if not candidate_origin:
        # Check host header matching
        host = request.headers.get("host")
        if host in ("localhost", "127.0.0.1", "test", "testserver") or "127.0.0.1:" in str(host) or "localhost:" in str(host):
            return await call_next(request)
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "message": "Cross-Site Request Forgery validation failed: missing origin header.",
                    "status_code": 403,
                }
            },
        )

    # Normalize allowed origins
    allowed = set(settings.cors_origins)
    allowed.add("http://localhost:5173")
    allowed.add("http://127.0.0.1:5173")
    allowed.add("http://localhost:3000")
    allowed.add("http://test")
    allowed.add("http://testserver")
    allowed.add("https://safeapply-live-app-g0f0hte3g8fmfcgw.indiasouthcentral-01.azurewebsites.net")

    # Dynamic Same-Origin allowance from Request Host header
    host = request.headers.get("host")
    if host:
        allowed.add(f"https://{host}")
        allowed.add(f"http://{host}")

    # Match candidate origin
    if candidate_origin not in allowed and not any(candidate_origin.startswith(a) for a in allowed):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "message": f"Cross-Site Request Forgery validation failed: origin '{candidate_origin}' not permitted.",
                    "status_code": 403,
                }
            },
        )

    return await call_next(request)
