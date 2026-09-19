"""
In-memory sliding window rate limiter for public API protection.
Limits abusive request volumes per IP and session for sensitive endpoints.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, status
from fastapi.responses import JSONResponse
from backend.config import settings


class SlidingWindowRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._records: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Check if request is allowed under the sliding window limit.
        Returns: (is_allowed, seconds_to_wait)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            timestamps = self._records[key]
            # Prune timestamps outside window
            valid_timestamps = [t for t in timestamps if t > window_start]
            self._records[key] = valid_timestamps

            if len(valid_timestamps) >= max_requests:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)))
                return False, retry_after

            valid_timestamps.append(now)
            return True, 0

    def cleanup(self):
        """Periodic cleanup of stale keys."""
        now = time.time()
        window_start = now - 120
        with self._lock:
            stale_keys = [k for k, ts in self._records.items() if not ts or ts[-1] < window_start]
            for k in stale_keys:
                del self._records[k]


limiter = SlidingWindowRateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    if not settings.rate_limit_enabled:
        return await call_next(request)

    path = request.url.path
    method = request.method

    # Determine endpoint limit category
    category = None
    max_rpm = 120

    if path.startswith("/api/v1/analysis"):
        category = "analysis"
        max_rpm = settings.rate_limit_analysis_rpm
    elif path.startswith("/api/v1/profile/resume") and method == "POST":
        category = "upload"
        max_rpm = settings.rate_limit_upload_rpm
    elif "/send" in path and method == "POST":
        category = "send"
        max_rpm = 15
    elif path.startswith("/api/v1/mailboxes/sync"):
        category = "sync"
        max_rpm = 10

    if category:
        # Key on client IP or session cookie
        client_ip = request.client.host if request.client else "unknown"
        cookie_token = request.cookies.get(settings.cookie_name, "")
        key = f"{category}:{client_ip}:{cookie_token[:10]}"

        allowed, retry_after = limiter.is_allowed(key=key, max_requests=max_rpm, window_seconds=60)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "message": f"Rate limit exceeded for {category}. Please wait {retry_after} seconds.",
                        "status_code": 429,
                        "retry_after": retry_after,
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

    return await call_next(request)
