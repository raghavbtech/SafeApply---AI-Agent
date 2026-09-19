"""Verification schemas for Medium-Risk offers."""

from typing import List, Optional
from pydantic import BaseModel


class VerificationChecklistItem(BaseModel):
    id: str
    risk_type: str
    description: str
    recommended_action: str
    verified: bool = False


class VerificationChecklistResponse(BaseModel):
    email_id: str
    original_risk_score: int
    original_risk_level: str
    review_status: str  # unreviewed | in_review | verified | rejected
    user_override: Optional[str] = None
    checklist: List[VerificationChecklistItem]


class VerificationUpdateRequest(BaseModel):
    checklist_answers: List[VerificationChecklistItem]
    override_to_trusted: bool = False
    candidate_notes: Optional[str] = None
