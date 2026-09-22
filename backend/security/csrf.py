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

    if not candidate_origin:
        # Check host header matching
        host = request.headers.get("host") or request.headers.get("x-forwarded-host")
        if not host or host in ("localhost", "127.0.0.1", "test", "testserver") or "127.0.0.1:" in str(host) or "localhost:" in str(host) or "azurewebsites.net" in str(host):
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

    norm_origin = candidate_origin.strip().rstrip("/")
    if "azurewebsites.net" in norm_origin:
        return await call_next(request)

    # Normalize allowed origins
    allowed_list = [
        o.strip().rstrip("/")
        for o in (
            settings.cors_origins
            + [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://test",
                "http://testserver",
                "https://safeapply-live-app-g0f0hte3g8fmfcgw.indiasouthcentral-01.azurewebsites.net",
            ]
        )
    ]

    host = request.headers.get("host")
    xf_host = request.headers.get("x-forwarded-host")
    for h in (host, xf_host):
        if h:
            h_clean = h.split(":")[0]
            allowed_list.append(f"https://{h}")
            allowed_list.append(f"http://{h}")
            allowed_list.append(f"https://{h_clean}")
            allowed_list.append(f"http://{h_clean}")

    if any(norm_origin == a or norm_origin.startswith(a) for a in allowed_list):
        return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": {
                "message": f"Cross-Site Request Forgery validation failed: origin '{candidate_origin}' not permitted.",
                "status_code": 403,
            }
        },
    )
