"""
Candidate profile and resume management service.
Enforces file-type validation, size limits, private storage, and data erasure.
"""

import os
import re
from datetime import datetime, timezone
from typing import Optional
from backend.config import settings
from backend.errors import NotFoundError, ValidationError
from backend.schemas.profile import CandidateProfileSchema, ResumeUploadResponse
from backend.adapters.repository import RepositoryAdapter
import job_agent


class ProfileService:
    MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def get_profile(user_id: str) -> CandidateProfileSchema:
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        is_comp = job_agent.is_candidate_profile_complete(prof) if prof else False
        return CandidateProfileSchema(
            full_name=prof.get("full_name") or "",
            email=prof.get("email") or "",
            phone=prof.get("phone") or "",
            education=prof.get("education") or "",
            university=prof.get("university") or "",
            gpa=prof.get("gpa") or "",
            skills=prof.get("skills") or [],
            experience=prof.get("experience") or "",
            preferred_roles=prof.get("preferred_roles") or [],
            target_locations=prof.get("target_locations") or [],
            portfolio_url=prof.get("portfolio_url") or "",
            linkedin_url=prof.get("linkedin_url") or "",
            resume_path=prof.get("resume_path") or "",
            resume_filename=prof.get("resume_filename") or "",
            is_complete=is_comp,
        )

    @staticmethod
    def update_profile(profile_data: CandidateProfileSchema, user_id: str) -> CandidateProfileSchema:
        existing = RepositoryAdapter.get_candidate_profile(user_id)
        merged = dict(existing)
        data = profile_data.model_dump()
        merged.update({k: v for k, v in data.items() if k != "is_complete"})
        
        RepositoryAdapter.save_candidate_profile(merged, user_id)
        is_comp = job_agent.is_candidate_profile_complete(merged)
        
        return CandidateProfileSchema(
            full_name=merged.get("full_name") or "",
            email=merged.get("email") or "",
            phone=merged.get("phone") or "",
            education=merged.get("education") or "",
            university=merged.get("university") or "",
            gpa=merged.get("gpa") or "",
            skills=merged.get("skills") or [],
            experience=merged.get("experience") or "",
            preferred_roles=merged.get("preferred_roles") or [],
            target_locations=merged.get("target_locations") or [],
            portfolio_url=merged.get("portfolio_url") or "",
            linkedin_url=merged.get("linkedin_url") or "",
            resume_path=merged.get("resume_path") or "",
            resume_filename=merged.get("resume_filename") or "",
            is_complete=is_comp,
        )

    @classmethod
    def save_resume(cls, filename: str, content: bytes, content_type: str, user_id: str) -> ResumeUploadResponse:
        if not content or len(content) < 10:
            raise ValidationError("Resume file cannot be empty.")

        if len(content) > cls.MAX_RESUME_BYTES:
            raise ValidationError("Resume exceeds maximum allowed size of 10MB.")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".pdf", ".docx", ".txt"):
            raise ValidationError("Supported resume formats are PDF, DOCX, and TXT.")

        # File signature / magic bytes validation
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            raise ValidationError("Invalid PDF format. File signature mismatch.")
        elif ext == ".docx" and not content.startswith(b"PK\x03\x04"):
            raise ValidationError("Invalid DOCX format. File signature mismatch.")
        elif ext == ".txt":
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValidationError("Invalid text file encoding. UTF-8 required.")

        # Private storage directory - never mounted statically
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        upload_dir = os.path.join(project_root, settings.uploads_dir)
        os.makedirs(upload_dir, exist_ok=True)

        # Sanitize filename with visitor session prefix
        clean_name = re.sub(r"[^\w\.-]", "_", os.path.basename(filename))
        safe_prefix = re.sub(r"[^\w]", "_", user_id)[:16]
        safe_name = f"resume_{safe_prefix}_{clean_name}"
        target_path = os.path.abspath(os.path.join(upload_dir, safe_name))

        # Delete any previous resume file for this session
        cls.delete_resume(user_id)

        with open(target_path, "wb") as f:
            f.write(content)

        # Update candidate profile state
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        prof["resume_path"] = target_path
        prof["resume_filename"] = filename
        RepositoryAdapter.save_candidate_profile(prof, user_id)

        return ResumeUploadResponse(
            filename=filename,
            file_size_bytes=len(content),
            content_type=content_type,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            is_active=True,
        )

    @classmethod
    def delete_resume(cls, user_id: str) -> bool:
        """Permanently delete resume file on disk and clear references."""
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        path = prof.get("resume_path")
        deleted = False
        if path and os.path.exists(path):
            try:
                os.remove(path)
                deleted = True
            except OSError:
                pass
        
        prof["resume_path"] = ""
        prof["resume_filename"] = ""
        RepositoryAdapter.save_candidate_profile(prof, user_id)
        return deleted

    @classmethod
    def delete_profile(cls, user_id: str) -> bool:
        """Permanently erase candidate profile and associated resume."""
        cls.delete_resume(user_id)
        RepositoryAdapter.delete_candidate_profile(user_id)
        return True

    @staticmethod
    def get_resume_file(user_id: str) -> str:
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        path = prof.get("resume_path")
        if not path or not os.path.exists(path):
            raise NotFoundError(resource="Resume", identifier="active_resume")
        return path
