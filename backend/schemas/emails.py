"""Email schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.schemas.analysis import AnalysisResultResponse


class EmailListItem(BaseModel):
    id: str
    message_id: Optional[str] = None
    imap_uid: Optional[str] = None
    sender: str
    sender_name: Optional[str] = None
    subject: str
    date: Optional[str] = None
    company_name: Optional[str] = "Unknown"
    role_title: Optional[str] = "Not Specified"
    status: str = "unscanned"  # unscanned | scanned | error | applied | verified | quarantined
    folder: str = "inbox"      # inbox | spam
    mailbox_action: str = "none" # none | moved_to_junk | move_failed | restored
    user_decision: str = "none"  # none | applied | ignored
    is_recruitment: bool = True
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    quarantined_at: Optional[str] = None
    quarantine_reason: Optional[str] = None
    quarantined_automatically: Optional[bool] = False
    applied_at: Optional[str] = None
    synced_at: Optional[str] = None


class EmailDetailResponse(EmailListItem):
    body: str = ""
    analysis: Optional[Dict[str, Any]] = None
    original_risk_score: Optional[int] = None
    original_risk_level: Optional[str] = None
    user_override: Optional[str] = None
    application_package: Optional[Dict[str, Any]] = None
    submission_id: Optional[str] = None


class EmlImportResponse(BaseModel):
    id: str
    is_recruitment: bool
    subject: str
    sender: str
    sender_name: Optional[str] = None
    date: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    body_snippet: str
    status: str
