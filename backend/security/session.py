"""
Cryptographically secure server-side anonymous session store.
Zero accounts, zero passwords, strict isolated partitions.
"""

import hashlib
import os
import secrets
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from backend.config import settings
import azure_db


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a session token for secure server-side storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class SessionRecord(BaseModel):
    session_id: str
    token_hash: str
    created_at: str
    last_active_at: str
    expires_at: str
    user_agent: Optional[str] = None


class SessionPrincipal(BaseModel):
    session_id: str
    created_at: str
    is_new: bool = False

    @property
    def user_id(self) -> str:
        """Alias for database partition key compatibility."""
        if settings.safeapply_user_id and settings.environment != "testing":
            return settings.safeapply_user_id
        return self.session_id

    @property
    def email(self) -> str:
        if settings.safeapply_user_id:
            return settings.safeapply_user_id
        return f"{self.session_id}@anonymous.safeapply.local"

    @property
    def full_name(self) -> str:
        if settings.safeapply_user_id:
            return "Verified Candidate"
        return "Anonymous Candidate"

    @property
    def role(self) -> str:
        return "anonymous_candidate"


class SessionStore:
    """
    Thread-safe server-side store for anonymous visitor sessions.
    Persists to azure_db state bucket to survive worker restarts.
    """

    _lock = threading.Lock()
    # In-memory index: token_hash -> SessionRecord
    _sessions_by_hash: Dict[str, SessionRecord] = {}
    # session_id -> token_hash
    _hash_by_session_id: Dict[str, str] = {}
    _loaded_from_db: bool = False

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._loaded_from_db:
            return
        with cls._lock:
            if cls._loaded_from_db:
                return
            try:
                stored = azure_db.db_get_state("anonymous_sessions", default={})
                if isinstance(stored, dict):
                    for sess_id, data in stored.items():
                        try:
                            rec = SessionRecord(**data)
                            cls._sessions_by_hash[rec.token_hash] = rec
                            cls._hash_by_session_id[rec.session_id] = rec.token_hash
                        except Exception:
                            continue
            except Exception:
                pass
            cls._loaded_from_db = True

    @classmethod
    def _persist_state(cls) -> None:
        try:
            dumped = {
                rec.session_id: rec.model_dump()
                for rec in cls._sessions_by_hash.values()
            }
            azure_db.db_set_state("anonymous_sessions", dumped)
        except Exception:
            pass

    @classmethod
    def create_session(cls, user_agent: Optional[str] = None) -> Tuple[SessionPrincipal, str]:
        """
        Create a new unpredictable anonymous session.
        Returns (SessionPrincipal, raw_token). The raw token is sent to the client once via cookie.
        """
        cls._ensure_loaded()
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=settings.session_expire_days)

        # 12-byte hex for clean session ID, 32-byte URL-safe cryptographic token
        session_id = f"anon_{secrets.token_hex(12)}"
        raw_token = secrets.token_urlsafe(32)
        thash = hash_token(raw_token)

        rec = SessionRecord(
            session_id=session_id,
            token_hash=thash,
            created_at=now.isoformat(),
            last_active_at=now.isoformat(),
            expires_at=expires.isoformat(),
            user_agent=user_agent,
        )

        with cls._lock:
            cls._sessions_by_hash[thash] = rec
            cls._hash_by_session_id[session_id] = thash
            cls._persist_state()

        principal = SessionPrincipal(
            session_id=session_id,
            created_at=rec.created_at,
            is_new=True,
        )
        return principal, raw_token

    @classmethod
    def validate_session(cls, raw_token: str) -> Optional[SessionPrincipal]:
        """
        Validate incoming session token against SHA-256 hash.
        Renews last_active_at sliding expiration if valid.
        """
        if not raw_token or not isinstance(raw_token, str):
            return None

        cls._ensure_loaded()
        thash = hash_token(raw_token.strip())

        with cls._lock:
            rec = cls._sessions_by_hash.get(thash)
            if not rec:
                return None

            # Check expiration
            try:
                expires_dt = datetime.fromisoformat(rec.expires_at)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_dt:
                    # Expired: remove
                    cls._sessions_by_hash.pop(thash, None)
                    cls._hash_by_session_id.pop(rec.session_id, None)
                    cls._persist_state()
                    return None
            except Exception:
                return None

            # Sliding renewal: extend expiration
            now = datetime.now(timezone.utc)
            rec.last_active_at = now.isoformat()
            rec.expires_at = (now + timedelta(days=settings.session_expire_days)).isoformat()
            cls._persist_state()

            return SessionPrincipal(
                session_id=rec.session_id,
                created_at=rec.created_at,
                is_new=False,
            )

    @classmethod
    def delete_session(cls, session_id: str) -> bool:
        """Revoke and delete server-side session."""
        cls._ensure_loaded()
        with cls._lock:
            thash = cls._hash_by_session_id.pop(session_id, None)
            if thash:
                cls._sessions_by_hash.pop(thash, None)
                cls._persist_state()
                return True
            return False

    @classmethod
    def get_session_info(cls, session_id: str) -> Optional[SessionRecord]:
        cls._ensure_loaded()
        with cls._lock:
            thash = cls._hash_by_session_id.get(session_id)
            if thash:
                return cls._sessions_by_hash.get(thash)
            return None
