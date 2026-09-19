"""
Job Agent application service.
Guarantees human approval gate, preview/draft separation, and idempotent dispatch.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from backend.errors import ConflictError, NotFoundError, ValidationError
from backend.schemas.jobs import (
    ApplicationDraftResponse,
    ApplicationRecordResponse,
    ApplicationSendRequest,
    JobSpecResponse,
    MatchEvaluationResponse,
)
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.application_sender import ApplicationSenderAdapter
import job_agent


class ApplicationService:
    @staticmethod
    def preview_job(email_id: str, user_id: str) -> Dict[str, Any]:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        profile = RepositoryAdapter.get_candidate_profile(user_id)
        job_spec = ApplicationSenderAdapter.extract_job_spec(email.get("body", ""), email)
        match_res = ApplicationSenderAdapter.evaluate_match(job_spec, profile)

        is_no_rep = ApplicationSenderAdapter.is_no_reply(job_spec.get("contact_email") or email.get("sender", ""))

        return {
            "job_spec": JobSpecResponse(
                company_name=job_spec.get("company_name", "Not specified"),
                role_title=job_spec.get("role_title", "Not specified"),
                location=job_spec.get("location", "Not specified"),
                salary=job_spec.get("salary", "Not specified"),
                required_skills=job_spec.get("required_skills", []),
                portal_url=job_spec.get("portal_url", "Not specified"),
                contact_email=job_spec.get("contact_email", "Not specified"),
                is_no_reply=is_no_rep,
            ),
            "match_evaluation": MatchEvaluationResponse(
                match_percentage=match_res["match_percentage"],
                match_rating=match_res["match_rating"],
                match_badge_color=match_res["match_badge_color"],
                matched_skills=match_res["matched_skills"],
                missing_skills=match_res["missing_skills"],
                total_required=match_res["total_required"],
                candidate_skills_count=match_res["candidate_skills_count"],
            ),
        }

    @staticmethod
    def generate_draft(email_id: str, user_id: str) -> ApplicationDraftResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        profile = RepositoryAdapter.get_candidate_profile(user_id)
        job_spec = ApplicationSenderAdapter.extract_job_spec(email.get("body", ""), email)
        match_res = ApplicationSenderAdapter.evaluate_match(job_spec, profile)
        draft_pkg = ApplicationSenderAdapter.generate_draft(job_spec, profile, fast_mode=False)

        target_em = job_spec.get("contact_email") or email.get("sender", "recruiter@example.com")
        is_no_rep = ApplicationSenderAdapter.is_no_reply(target_em)

        resume_name = profile.get("resume_filename") or "Candidate_Resume.pdf"

        return ApplicationDraftResponse(
            email_id=email_id,
            job_spec=JobSpecResponse(
                company_name=job_spec.get("company_name", "Not specified"),
                role_title=job_spec.get("role_title", "Not specified"),
                location=job_spec.get("location", "Not specified"),
                salary=job_spec.get("salary", "Not specified"),
                required_skills=job_spec.get("required_skills", []),
                portal_url=job_spec.get("portal_url", "Not specified"),
                contact_email=job_spec.get("contact_email", "Not specified"),
                is_no_reply=is_no_rep,
            ),
            match_evaluation=MatchEvaluationResponse(
                match_percentage=match_res["match_percentage"],
                match_rating=match_res["match_rating"],
                match_badge_color=match_res["match_badge_color"],
                matched_skills=match_res["matched_skills"],
                missing_skills=match_res["missing_skills"],
                total_required=match_res["total_required"],
                candidate_skills_count=match_res["candidate_skills_count"],
            ),
            cover_letter=draft_pkg.get("cover_letter", ""),
            recruiter_reply=draft_pkg.get("recruiter_reply", ""),
            qa_talking_points=draft_pkg.get("qa_talking_points", ""),
            resume_filename=resume_name,
            target_email=target_em,
            is_no_reply=is_no_rep,
        )

    @staticmethod
    def send_approved(email_id: str, send_req: ApplicationSendRequest, user_id: str) -> ApplicationRecordResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        # Idempotency check: prevent duplicate sends
        if email.get("status") == "applied" and email.get("submission_id"):
            apps = RepositoryAdapter.get_applied_jobs(user_id)
            existing_app = next((a for a in apps if a.get("email_id") == email_id), None)
            if existing_app:
                return ApplicationRecordResponse(
                    submission_id=existing_app["submission_id"],
                    email_id=email_id,
                    company_name=existing_app.get("company_name", "Not specified"),
                    role_title=existing_app.get("role_title", "Not specified"),
                    applied_at=existing_app.get("applied_at", ""),
                    candidate_name=existing_app.get("candidate_name", "Candidate"),
                    candidate_email=existing_app.get("candidate_email", user_id),
                    portal_url=existing_app.get("portal_url", "Not specified"),
                    recruiter_email=existing_app.get("recruiter_email", "Not specified"),
                    cover_letter_snippet=existing_app.get("cover_letter_snippet", ""),
                    recruiter_reply=existing_app.get("recruiter_reply"),
                    is_no_reply=existing_app.get("is_no_reply", False),
                    dispatch_status=existing_app.get("dispatch_status", "Applied"),
                    dispatch_notice=existing_app.get("dispatch_notice"),
                    status=existing_app.get("status", "Applied"),
                    resume_filename=existing_app.get("resume_filename"),
                )

        profile = RepositoryAdapter.get_candidate_profile(user_id)
        job_spec = ApplicationSenderAdapter.extract_job_spec(email.get("body", ""), email)

        app_package = {
            "cover_letter": send_req.approved_cover_letter,
            "recruiter_reply": send_req.approved_recruiter_reply,
        }

        # Dispatch
        sub_rec = ApplicationSenderAdapter.send_approved_application(
            email_id=email_id,
            job_spec=job_spec,
            application_package=app_package,
            candidate_profile=profile,
            email_data=email,
        )

        # Explicitly save applied job under authenticated user_id
        RepositoryAdapter.save_applied_job(sub_rec, user_id=user_id)

        # Update email state in store

        RepositoryAdapter.update_email(
            email_id,
            {
                "status": "applied",
                "user_decision": "applied",
                "applied_at": sub_rec.get("applied_at"),
                "submission_id": sub_rec.get("submission_id"),
                "application_package": app_package,
            },
            user_id,
        )

        # Write audit record
        RepositoryAdapter.write_audit(
            action="submit_application",
            email_id=email_id,
            details={
                "submission_id": sub_rec.get("submission_id"),
                "company_name": job_spec.get("company_name"),
                "role_title": job_spec.get("role_title"),
                "is_no_reply": sub_rec.get("is_no_reply"),
                "status": sub_rec.get("status"),
            },
            user_id=user_id,
        )

        return ApplicationRecordResponse(
            submission_id=sub_rec["submission_id"],
            email_id=email_id,
            company_name=sub_rec.get("company_name", "Not specified"),
            role_title=sub_rec.get("role_title", "Not specified"),
            applied_at=sub_rec.get("applied_at", ""),
            candidate_name=sub_rec.get("candidate_name", "Candidate"),
            candidate_email=sub_rec.get("candidate_email", user_id),
            portal_url=sub_rec.get("portal_url", "Not specified"),
            recruiter_email=sub_rec.get("recruiter_email", "Not specified"),
            cover_letter_snippet=sub_rec.get("cover_letter_snippet", ""),
            recruiter_reply=sub_rec.get("recruiter_reply"),
            is_no_reply=sub_rec.get("is_no_reply", False),
            dispatch_status=sub_rec.get("dispatch_status", "Applied"),
            dispatch_notice=sub_rec.get("dispatch_notice"),
            status=sub_rec.get("status", "Applied"),
            resume_filename=sub_rec.get("resume_filename"),
        )

    @staticmethod
    def list_applications(user_id: str) -> List[ApplicationRecordResponse]:
        apps = RepositoryAdapter.get_applied_jobs(user_id)
        return [
            ApplicationRecordResponse(
                submission_id=a["id"] if "id" in a and not a.get("submission_id") else a.get("submission_id", "APP-REC"),
                email_id=a.get("email_id", ""),
                company_name=a.get("company_name", "Not specified"),
                role_title=a.get("role_title", "Not specified"),
                applied_at=a.get("applied_at") or a.get("recorded_at", ""),
                candidate_name=a.get("candidate_name", "Candidate"),
                candidate_email=a.get("candidate_email", user_id),
                portal_url=a.get("portal_url", "Not specified"),
                recruiter_email=a.get("recruiter_email", "Not specified"),
                cover_letter_snippet=a.get("cover_letter_snippet", ""),
                recruiter_reply=a.get("recruiter_reply"),
                is_no_reply=a.get("is_no_reply", False),
                dispatch_status=a.get("dispatch_status", "Applied"),
                dispatch_notice=a.get("dispatch_notice"),
                status=a.get("status", "Applied"),
                resume_filename=a.get("resume_filename"),
            )
            for a in apps
        ]
