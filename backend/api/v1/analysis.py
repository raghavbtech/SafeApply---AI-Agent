"""
Risk analysis endpoints.
"""

from fastapi import APIRouter, Depends
from backend.schemas.analysis import AdHocAnalysisRequest, AnalysisResultResponse
from backend.schemas.auth import UserPrincipal
from backend.services.analysis_service import AnalysisService
from backend.dependencies import get_current_user

router = APIRouter(tags=["Analysis"])


@router.post("/analysis/text", response_model=AnalysisResultResponse)
async def analyze_text(
    req: AdHocAnalysisRequest,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return AnalysisService.analyze_text(text=req.text, fast_mode=req.fast_mode, source=req.source or "adhoc")


@router.post("/emails/{email_id}/analyze", response_model=AnalysisResultResponse)
async def analyze_stored_email(
    email_id: str,
    fast_mode: bool = False,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return AnalysisService.analyze_stored_email(
        email_id=email_id, user_id=current_user.user_id, fast_mode=fast_mode
    )


@router.get("/emails/{email_id}/analysis", response_model=AnalysisResultResponse)
async def get_stored_email_analysis(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return AnalysisService.get_email_analysis(email_id=email_id, user_id=current_user.user_id)
