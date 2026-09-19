"""
Identity and token management using PyJWT.
"""

import hashlib
import hmac
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import jwt

from backend.config import settings
from backend.schemas.auth import UserPrincipal


def hash_password(password: str, salt: str = "safeapply-salt-2026") -> str:
    """Hash password with SHA256 and fixed salt."""
    key = salt.encode("utf-8")
    msg = password.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_password(plain_password: str, hashed_password: str, salt: str = "safeapply-salt-2026") -> bool:
    return hmac.compare_digest(hash_password(plain_password, salt), hashed_password)


def create_access_token(user: UserPrincipal, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        "sub": user.user_id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[UserPrincipal]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if not user_id or not email:
            return None
        return UserPrincipal(
            user_id=user_id,
            email=email,
            full_name=payload.get("full_name"),
            role=payload.get("role", "candidate"),
        )
    except (jwt.PyJWTError, Exception):
        return None
