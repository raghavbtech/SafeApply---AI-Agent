"""Mailbox actions and connection schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MailboxConnectionStatus(BaseModel):
    provider: str
    username: str
    is_connected: bool
    status: str  # connected | disconnected | degraded
    imap_server: Optional[str] = None
    imap_port: Optional[int] = None
    last_sync: Optional[str] = None
    stored_count: int = 0


class ConnectMailboxRequest(BaseModel):
    provider: str = "Gmail"
    username: str
    password_or_app_token: str
    imap_server: Optional[str] = None
    imap_port: int = 993


class SyncMailboxRequest(BaseModel):
    max_messages: int = Field(default=15, ge=1, le=100)


class SyncMailboxResult(BaseModel):
    ok: bool
    inspected: int = 0
    recruitment: int = 0
    skipped: int = 0
    new_stored: int = 0
    error: Optional[str] = None
    synced_at: str


class SpamActionRequest(BaseModel):
    reason: str = "Manually quarantined by candidate"


class SpamActionResponse(BaseModel):
    ok: bool
    mailbox_moved: bool
    local_quarantined: bool = False
    error: Optional[str] = None
    audit_id: Optional[str] = None


class RestoreActionResponse(BaseModel):
    ok: bool
    mailbox_restored: bool
    error: Optional[str] = None
    audit_id: Optional[str] = None


class BatchScanResult(BaseModel):
    total_unscanned: int
    scanned_count: int
    quarantined_count: int
    applied_count: int
    results: List[Dict[str, Any]]
