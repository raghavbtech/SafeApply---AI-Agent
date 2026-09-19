"""
Candidate Profile and Resume endpoints.
"""

import os
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from backend.schemas.profile import CandidateProfileSchema, ResumeUploadResponse
from backend.schemas.auth import UserPrincipal
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
    file_path = ProfileService.get_resume_file(user_id=current_user.user_id)
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=os.path.basename(file_path),
    )
