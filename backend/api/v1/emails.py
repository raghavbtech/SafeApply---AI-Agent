"""
Emails and inbox management endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile
from backend.schemas.emails import EmailDetailResponse, EmlImportResponse
from backend.schemas.mailbox import BatchScanResult
from backend.schemas.auth import UserPrincipal
from backend.services.mailbox_service import MailboxService
from backend.dependencies import get_current_user

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get("")
async def list_emails(
    folder: Optional[str] = Query("inbox", description="inbox or spam"),
    status: Optional[str] = Query(None, description="unscanned, scanned, applied, verified, quarantined"),
    risk_level: Optional[str] = Query(None, description="Low, Medium, High, Critical"),
    search: Optional[str] = Query(None, description="search keyword in subject, sender, company"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserPrincipal = Depends(get_current_user),
):
    return MailboxService.list_emails(
        user_id=current_user.user_id,
        folder=folder,
        status=status,
        risk_level=risk_level,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{email_id}", response_model=EmailDetailResponse)
async def get_email(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return MailboxService.get_email(email_id=email_id, user_id=current_user.user_id)


@router.post("/import-eml", response_model=EmlImportResponse)
async def import_eml(
    file: UploadFile = File(...),
    current_user: UserPrincipal = Depends(get_current_user),
):
    content = await file.read()
    return MailboxService.import_eml(content_bytes=content, user_id=current_user.user_id)


@router.post("/batch-scan", response_model=BatchScanResult)
async def batch_scan_emails(
    limit: int = Query(50, ge=1, le=100),
    current_user: UserPrincipal = Depends(get_current_user),
):
    return MailboxService.batch_scan_unscanned(user_id=current_user.user_id, limit=limit)
