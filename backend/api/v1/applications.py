"""
Job Agent application draft, preview, approved dispatch, and history endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from backend.schemas.jobs import (
    ApplicationDraftResponse,
    ApplicationRecordResponse,
    ApplicationSendRequest,
)
from backend.schemas.auth import UserPrincipal
from backend.services.application_service import ApplicationService
from backend.dependencies import get_current_user

router = APIRouter(tags=["Job Applications"])


@router.get("/jobs/{email_id}/preview")
async def preview_job(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ApplicationService.preview_job(email_id=email_id, user_id=current_user.user_id)


@router.post("/jobs/{email_id}/draft", response_model=ApplicationDraftResponse)
async def generate_draft(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ApplicationService.generate_draft(email_id=email_id, user_id=current_user.user_id)


@router.post("/jobs/{email_id}/send", response_model=ApplicationRecordResponse)
async def send_approved_application(
    email_id: str,
    send_req: ApplicationSendRequest,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ApplicationService.send_approved(
        email_id=email_id, send_req=send_req, user_id=current_user.user_id
    )


@router.get("/applications", response_model=List[ApplicationRecordResponse])
async def list_applications(
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ApplicationService.list_applications(user_id=current_user.user_id)
