"""
Redaction utility for logs and safe client output.
"""

import re
from typing import Any, Dict


REDACTED = "[REDACTED]"

SENSITIVE_PATTERNS = [
    (re.compile(r"(password|secret|token|api_key|app_password)\s*[:=]\s*['\"]?([^'\"\s]+)", re.I), r"\1=" + REDACTED),
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.I), "Bearer " + REDACTED),
]


def redact_text(text: str) -> str:
    if not text:
        return ""
    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    safe = {}
    for k, v in data.items():
        if any(s in k.lower() for s in ("password", "secret", "key", "token", "auth")):
            safe[k] = REDACTED
        elif isinstance(v, dict):
            safe[k] = redact_dict(v)
        elif isinstance(v, str):
            safe[k] = redact_text(v)
        else:
            safe[k] = v
    return safe
