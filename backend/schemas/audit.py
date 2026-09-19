"""Audit log and hash chain schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class AuditRecordSchema(BaseModel):
    id: str
    sequence: int
    action: str
    email_doc_id: Optional[str] = None
    timestamp: str
    details: Dict[str, Any] = {}
    prev_hash: str
    record_hash: str


class AuditChainStatusResponse(BaseModel):
    valid: bool
    records: int
    broken_at: Optional[int] = None
    reason: Optional[str] = None
