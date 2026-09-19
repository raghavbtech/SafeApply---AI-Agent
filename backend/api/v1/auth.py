"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, Response
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPrincipal
from backend.services.auth_service import AuthService
from backend.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(login_req: LoginRequest, response: Response):
    res = AuthService.authenticate(login_req)
    # Also set secure HTTP-only session cookie
    response.set_cookie(
        key="safeapply_session",
        value=res.access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in HTTPS production
        max_age=86400,
    )
    return res


@router.post("/register", response_model=TokenResponse)
async def register(reg_req: RegisterRequest, response: Response):
    res = AuthService.register(reg_req)
    response.set_cookie(
        key="safeapply_session",
        value=res.access_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
    )
    return res


@router.get("/me", response_model=UserPrincipal)
async def get_me(current_user: UserPrincipal = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="safeapply_session")
    return {"message": "Logged out successfully.", "success": True}
