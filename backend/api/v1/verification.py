"""
Verification endpoints for Medium-Risk offers.
"""

from fastapi import APIRouter, Depends
from backend.schemas.verification import (
    VerificationChecklistResponse,
    VerificationUpdateRequest,
)
from backend.schemas.auth import UserPrincipal
from backend.services.verification_service import VerificationService
from backend.dependencies import get_current_user

router = APIRouter(prefix="/emails", tags=["Verification"])


@router.get("/{email_id}/verification", response_model=VerificationChecklistResponse)
async def get_verification_checklist(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return VerificationService.get_checklist(email_id=email_id, user_id=current_user.user_id)


@router.post("/{email_id}/verification", response_model=VerificationChecklistResponse)
async def update_verification(
    email_id: str,
    update_req: VerificationUpdateRequest,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return VerificationService.update_verification(
        email_id=email_id, update_req=update_req, user_id=current_user.user_id
    )
