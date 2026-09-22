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
        result = CandidateProfileSchema(
            full_name=prof.get("full_name") or "",
            email=prof.get("email") or "",
            phone=prof.get("phone") or "",
            education=prof.get("education") or "",
            university=prof.get("university") or "",
            cgpa=prof.get("cgpa") or prof.get("gpa") or "",
            grading_scale=prof.get("grading_scale") or "",
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
        try:
            result.validate_cgpa_against_scale()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return result

    @staticmethod
    def update_profile(profile_data: CandidateProfileSchema, user_id: str) -> CandidateProfileSchema:
        existing = RepositoryAdapter.get_candidate_profile(user_id)
        merged = dict(existing)
        data = profile_data.model_dump()
        try:
            profile_data.validate_cgpa_against_scale()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        data.pop("gpa", None)
        merged.update({k: v for k, v in data.items() if k != "is_complete"})
        merged.pop("gpa", None)
        
        RepositoryAdapter.save_candidate_profile(merged, user_id)
        is_comp = job_agent.is_candidate_profile_complete(merged)
        
        result = CandidateProfileSchema(
            full_name=merged.get("full_name") or "",
            email=merged.get("email") or "",
            phone=merged.get("phone") or "",
            education=merged.get("education") or "",
            university=merged.get("university") or "",
            cgpa=merged.get("cgpa") or "",
            grading_scale=merged.get("grading_scale") or "",
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
        try:
            result.validate_cgpa_against_scale()
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return result

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

        # Upload via BlobStorageAdapter (Azure Blob with local fallback)
        from backend.adapters.blob_storage import BlobStorageAdapter
        opaque_ref, clean_name = BlobStorageAdapter.upload_resume(
            user_id=user_id,
            filename=filename,
            content=content,
            content_type=content_type,
        )

        # Update candidate profile state
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        prof["resume_opaque_ref"] = opaque_ref
        prof["resume_path"] = opaque_ref
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
        """Permanently delete resume from blob/disk storage and clear references."""
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        opaque_ref = prof.get("resume_opaque_ref") or prof.get("resume_path")
        
        from backend.adapters.blob_storage import BlobStorageAdapter
        deleted = False
        if opaque_ref:
            deleted = BlobStorageAdapter.delete_resume(opaque_ref, user_id)
        BlobStorageAdapter.purge_user_resumes(user_id)
        
        prof["resume_opaque_ref"] = ""
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
    def get_resume_bytes(user_id: str) -> tuple[bytes, str, str]:
        """Download resume bytes, original filename, and media type."""
        prof = RepositoryAdapter.get_candidate_profile(user_id)
        opaque_ref = prof.get("resume_opaque_ref") or prof.get("resume_path")
        if not opaque_ref:
            raise NotFoundError(resource="Resume", identifier="active_resume")

        from backend.adapters.blob_storage import BlobStorageAdapter
        res = BlobStorageAdapter.download_resume(opaque_ref, user_id)
        if not res:
            raise NotFoundError(resource="Resume", identifier="active_resume")
        
        content, fname, ctype = res
        orig_filename = prof.get("resume_filename") or fname
        media_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        ctype = media_types.get(os.path.splitext(orig_filename)[1].lower(), ctype)
        return content, orig_filename, ctype

    @staticmethod
    def get_resume_file(user_id: str) -> str:
        """Compatibility helper returning a readable local file path."""
        content, fname, _ = ProfileService.get_resume_bytes(user_id)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        safe_user = re.sub(r"[^\w]", "_", user_id)[:32]
        temp_dir = os.path.join(project_root, settings.uploads_dir, safe_user)
        os.makedirs(temp_dir, exist_ok=True)
        local_path = os.path.join(temp_dir, fname)
        with open(local_path, "wb") as f:
            f.write(content)
        return local_path
