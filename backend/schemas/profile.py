"""Candidate profile and resume schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CandidateProfileSchema(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: Optional[str] = ""
    education: Optional[str] = ""
    university: Optional[str] = ""
    cgpa: Optional[str] = ""
    grading_scale: Optional[str] = ""
    skills: List[str] = []
    experience: Optional[str] = ""
    preferred_roles: List[str] = []
    target_locations: List[str] = []
    portfolio_url: Optional[str] = ""
    linkedin_url: Optional[str] = ""
    resume_path: Optional[str] = ""
    resume_filename: Optional[str] = ""
    is_complete: bool = False

    @field_validator("cgpa")
    @classmethod
    def validate_cgpa(cls, value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return ""
        try:
            score = float(value)
        except ValueError as exc:
            raise ValueError("CGPA must be numeric.") from exc
        if score < 0:
            raise ValueError("CGPA cannot be negative.")
        return value.strip()

    @field_validator("grading_scale")
    @classmethod
    def validate_grading_scale(cls, value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return ""
        try:
            scale = float(value)
        except ValueError as exc:
            raise ValueError("Grading scale must be numeric.") from exc
        if scale <= 0:
            raise ValueError("Grading scale must be greater than zero.")
        return value.strip()

    def validate_cgpa_against_scale(self) -> None:
        if self.cgpa and self.grading_scale and float(self.cgpa) > float(self.grading_scale):
            raise ValueError("CGPA cannot exceed the selected grading scale.")


class ResumeUploadResponse(BaseModel):
    filename: str
    file_size_bytes: int
    content_type: str
    uploaded_at: str
    is_active: bool = True
