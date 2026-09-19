"""Candidate profile and resume schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CandidateProfileSchema(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: Optional[str] = ""
    education: Optional[str] = ""
    university: Optional[str] = ""
    gpa: Optional[str] = ""
    skills: List[str] = []
    experience: Optional[str] = ""
    preferred_roles: List[str] = []
    target_locations: List[str] = []
    portfolio_url: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    resume_path: Optional[str] = ""
    resume_filename: Optional[str] = ""
    is_complete: bool = False


class ResumeUploadResponse(BaseModel):
    filename: str
    file_size_bytes: int
    content_type: str
    uploaded_at: str
    is_active: bool = True
