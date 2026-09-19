"""Job Agent, match evaluation, and application dispatch schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobSpecResponse(BaseModel):
    company_name: str = "Not specified"
    role_title: str = "Not specified"
    location: str = "Not specified"
    salary: str = "Not specified"
    required_skills: List[str] = []
    portal_url: str = "Not specified"
    contact_email: str = "Not specified"
    is_no_reply: bool = False


class MatchEvaluationResponse(BaseModel):
    match_percentage: int
    match_rating: str
    match_badge_color: str
    matched_skills: List[str]
    missing_skills: List[str]
    total_required: int
    candidate_skills_count: int


class ApplicationDraftResponse(BaseModel):
    email_id: str
    job_spec: JobSpecResponse
    match_evaluation: MatchEvaluationResponse
    cover_letter: str
    recruiter_reply: str
    qa_talking_points: str
    resume_filename: Optional[str] = None
    target_email: str
    is_no_reply: bool


class ApplicationDraftUpdateRequest(BaseModel):
    cover_letter: str
    recruiter_reply: str


class ApplicationSendRequest(BaseModel):
    approved_cover_letter: str
    approved_recruiter_reply: str
    idempotency_key: Optional[str] = None


class ApplicationRecordResponse(BaseModel):
    submission_id: str
    email_id: str
    company_name: str
    role_title: str
    applied_at: str
    candidate_name: str
    candidate_email: str
    portal_url: str
    recruiter_email: str
    cover_letter_snippet: str
    recruiter_reply: Optional[str] = None
    is_no_reply: bool = False
    dispatch_status: str
    dispatch_notice: Optional[str] = None
    status: str
    resume_filename: Optional[str] = None
