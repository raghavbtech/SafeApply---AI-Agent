"""
Risk analysis service wrapping 4-pillar detection pipeline.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from backend.errors import NotFoundError, ValidationError
from backend.schemas.analysis import AnalysisResultResponse, ToolOutputsResponse
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.security_engine import SecurityEngineAdapter


class AnalysisService:
    @staticmethod
    def analyze_text(text: str, fast_mode: bool = False, source: str = "adhoc") -> AnalysisResultResponse:
        if not text or len(text.strip()) < 10:
            raise ValidationError("Please provide at least 10 characters of offer text.")

        raw_res = SecurityEngineAdapter.analyze_text(text, fast_mode=fast_mode)

        tool_outs = raw_res.get("tool_outputs", {})
        return AnalysisResultResponse(
            analysis_id=f"adhoc_{int(datetime.now(timezone.utc).timestamp())}",
            email_id=None,
            risk_level=raw_res.get("risk_level", "Medium"),
            risk_score=raw_res.get("risk_score", 50),
            explanation=raw_res.get("explanation", ""),
            identified_red_flags=raw_res.get("identified_red_flags", []),
            extracted_data=raw_res.get("extracted_data", {}),
            tool_outputs=ToolOutputsResponse(
                rag_matches=tool_outs.get("rag_matches", []),
                domain_verification=tool_outs.get("domain_verification", {}),
                salary_sanity=tool_outs.get("salary_sanity", {}),
                ml_classifier=tool_outs.get("ml_classifier", {}),
            ),
            responsible_ai_disclaimer=raw_res.get("responsible_ai_disclaimer"),
            execution_mode=raw_res.get("execution_mode"),
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def analyze_stored_email(email_id: str, user_id: str, fast_mode: bool = False) -> AnalysisResultResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        raw_res = SecurityEngineAdapter.analyze_stored_email(email, fast_mode=fast_mode)

        # Update stored email with analysis verdict
        updates = {
            "status": "scanned",
            "risk_level": raw_res.get("risk_level", "Medium"),
            "risk_score": raw_res.get("risk_score", 50),
            "analysis": raw_res,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }

        # Update extracted company / role if not previously populated
        extracted = raw_res.get("extracted_data", {})
        if extracted.get("company_name") and email.get("company_name") in ("Unknown", "", None):
            updates["company_name"] = extracted["company_name"]
        if extracted.get("job_title") and email.get("role_title") in ("Not Specified", "", None):
            updates["role_title"] = extracted["job_title"]

        RepositoryAdapter.update_email(email_id, updates, user_id)

        # Write audit event
        RepositoryAdapter.write_audit(
            action="scan_email",
            email_id=email_id,
            details={
                "risk_level": raw_res.get("risk_level"),
                "risk_score": raw_res.get("risk_score"),
                "execution_mode": raw_res.get("execution_mode"),
            },
            user_id=user_id,
        )

        tool_outs = raw_res.get("tool_outputs", {})
        return AnalysisResultResponse(
            analysis_id=f"analysis_{email_id}",
            email_id=email_id,
            risk_level=raw_res.get("risk_level", "Medium"),
            risk_score=raw_res.get("risk_score", 50),
            explanation=raw_res.get("explanation", ""),
            identified_red_flags=raw_res.get("identified_red_flags", []),
            extracted_data=raw_res.get("extracted_data", {}),
            tool_outputs=ToolOutputsResponse(
                rag_matches=tool_outs.get("rag_matches", []),
                domain_verification=tool_outs.get("domain_verification", {}),
                salary_sanity=tool_outs.get("salary_sanity", {}),
                ml_classifier=tool_outs.get("ml_classifier", {}),
            ),
            responsible_ai_disclaimer=raw_res.get("responsible_ai_disclaimer"),
            execution_mode=raw_res.get("execution_mode"),
            scanned_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def get_email_analysis(email_id: str, user_id: str) -> AnalysisResultResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        raw_res = email.get("analysis")
        if not raw_res:
            # Trigger analysis on demand if not yet scanned
            return AnalysisService.analyze_stored_email(email_id, user_id)

        tool_outs = raw_res.get("tool_outputs", {})
        return AnalysisResultResponse(
            analysis_id=f"analysis_{email_id}",
            email_id=email_id,
            risk_level=email.get("risk_level", raw_res.get("risk_level", "Medium")),
            risk_score=email.get("risk_score", raw_res.get("risk_score", 50)),
            explanation=raw_res.get("explanation", ""),
            identified_red_flags=raw_res.get("identified_red_flags", []),
            extracted_data=raw_res.get("extracted_data", {}),
            tool_outputs=ToolOutputsResponse(
                rag_matches=tool_outs.get("rag_matches", []),
                domain_verification=tool_outs.get("domain_verification", {}),
                salary_sanity=tool_outs.get("salary_sanity", {}),
                ml_classifier=tool_outs.get("ml_classifier", {}),
            ),
            responsible_ai_disclaimer=raw_res.get("responsible_ai_disclaimer"),
            execution_mode=raw_res.get("execution_mode"),
            scanned_at=email.get("scanned_at"),
            review_status=email.get("user_override") or ("verified" if email.get("status") == "verified" else "unreviewed"),
        )
