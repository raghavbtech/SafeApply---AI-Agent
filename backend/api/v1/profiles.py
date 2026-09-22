"""
Candidate Profile and Resume endpoints.
"""

import os
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from backend.schemas.profile import CandidateProfileSchema, ResumeUploadResponse
from backend.schemas.auth import UserPrincipal
from backend.errors import SafeApplyError
from backend.services.profile_service import ProfileService
from backend.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=CandidateProfileSchema)
async def get_profile(current_user: UserPrincipal = Depends(get_current_user)):
    return ProfileService.get_profile(user_id=current_user.user_id)


@router.put("", response_model=CandidateProfileSchema)
async def update_profile(
    profile: CandidateProfileSchema,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ProfileService.update_profile(profile_data=profile, user_id=current_user.user_id)


@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserPrincipal = Depends(get_current_user),
):
    content = await file.read()
    return ProfileService.save_resume(
        filename=file.filename or "resume.pdf",
        content=content,
        content_type=file.content_type or "application/pdf",
        user_id=current_user.user_id,
    )


@router.get("/resume")
async def download_resume(current_user: UserPrincipal = Depends(get_current_user)):
    content, filename, media_type = ProfileService.get_resume_bytes(user_id=current_user.user_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/resume/preview")
async def preview_resume(current_user: UserPrincipal = Depends(get_current_user)):
    try:
        content, filename, media_type = ProfileService.get_resume_bytes(user_id=current_user.user_id)
    except SafeApplyError:
        raise
    except Exception as exc:
        raise SafeApplyError("Resume preview is temporarily unavailable.") from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/resume")
async def delete_resume(current_user: UserPrincipal = Depends(get_current_user)):
    deleted = ProfileService.delete_resume(user_id=current_user.user_id)
    return {"success": True, "deleted": deleted, "message": "Resume deleted successfully."}


@router.delete("")
async def delete_profile(current_user: UserPrincipal = Depends(get_current_user)):
    ProfileService.delete_profile(user_id=current_user.user_id)
    return {"success": True, "message": "Candidate profile and resume erased."}
