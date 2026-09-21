"""
Verification service for Medium-Risk ambiguous offers.
Preserves original assessment while recording candidate verification decisions.
"""

from datetime import datetime, timezone
from typing import List, Optional
from backend.errors import NotFoundError
from backend.schemas.verification import (
    VerificationChecklistItem,
    VerificationChecklistResponse,
    VerificationUpdateRequest,
)
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.security_engine import SecurityEngineAdapter


class VerificationService:
    @staticmethod
    def get_checklist(email_id: str, user_id: str) -> VerificationChecklistResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        raw_items = SecurityEngineAdapter.generate_checklist(email)
        checklist = [
            VerificationChecklistItem(
                id=item["id"],
                risk_type=item.get("risk_type", "General"),
                description=item.get("description", ""),
                recommended_action=item.get("recommended_action") or item.get("title") or "Review details",
                verified=bool(item.get("verified", item.get("completed", False))),
            )
            for item in raw_items
        ]

        orig_score = email.get("original_risk_score") or email.get("risk_score", 50)
        orig_level = email.get("original_risk_level") or email.get("risk_level", "Medium")

        return VerificationChecklistResponse(
            email_id=email_id,
            original_risk_score=orig_score,
            original_risk_level=orig_level,
            review_status="verified" if email.get("status") == "verified" else "in_review",
            user_override=email.get("user_override"),
            checklist=checklist,
        )

    @staticmethod
    def update_verification(
        email_id: str,
        update_req: VerificationUpdateRequest,
        user_id: str,
    ) -> VerificationChecklistResponse:
        email = RepositoryAdapter.fetch_email(email_id, user_id)
        if not email:
            raise NotFoundError(resource="Email", identifier=email_id)

        orig_score = email.get("original_risk_score") or email.get("risk_score", 50)
        orig_level = email.get("original_risk_level") or email.get("risk_level", "Medium")

        updates = {
            "original_risk_score": orig_score,
            "original_risk_level": orig_level,
        }

        if update_req.override_to_trusted:
            updates["status"] = "verified"
            updates["user_override"] = "Verified by Candidate"
            updates["user_decision"] = "verified"

        RepositoryAdapter.update_email(email_id, updates, user_id)

        # Write audit trail preserving original risk score
        RepositoryAdapter.write_audit(
            action="candidate_verification_override" if update_req.override_to_trusted else "update_verification",
            email_id=email_id,
            details={
                "original_risk_score": orig_score,
                "original_risk_level": orig_level,
                "override_to_trusted": update_req.override_to_trusted,
                "candidate_notes": update_req.candidate_notes,
                "checklist_answers": [item.model_dump() for item in update_req.checklist_answers],
            },
            user_id=user_id,
        )

        return VerificationChecklistResponse(
            email_id=email_id,
            original_risk_score=orig_score,
            original_risk_level=orig_level,
            review_status="verified" if update_req.override_to_trusted else "in_review",
            user_override=updates.get("user_override"),
            checklist=update_req.checklist_answers,
        )
