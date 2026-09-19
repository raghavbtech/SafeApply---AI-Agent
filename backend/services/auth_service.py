"""
Authentication and principal service.
"""

from typing import Optional
from backend.config import settings
from backend.errors import UnauthorizedError, ValidationError
from backend.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPrincipal
from backend.security.identity import create_access_token, hash_password, verify_password
from backend.adapters.repository import RepositoryAdapter


class AuthService:
    @staticmethod
    def authenticate(login_req: LoginRequest) -> TokenResponse:
        email = login_req.email.strip()
        # Allow default demo user login in development mode
        if settings.environment == "development" and (email in (settings.default_user_id, "demo@safeapply.local", "demo")):
            target_email = email if email != "demo" else settings.default_user_id
            principal = UserPrincipal(
                user_id=target_email,
                email=target_email,
                full_name="Aarav Sharma (Demo Candidate)",
                role="candidate",
            )
            token = create_access_token(principal)
            return TokenResponse(access_token=token, token_type="bearer", user=principal)


        # Check stored user profile credentials
        profile = RepositoryAdapter.get_candidate_profile(email)
        stored_hash = profile.get("password_hash")
        if not stored_hash or not verify_password(login_req.password, stored_hash):
            raise UnauthorizedError("Invalid email or password.")

        principal = UserPrincipal(
            user_id=email,
            email=email,
            full_name=profile.get("full_name") or email,
            role="candidate",
        )
        token = create_access_token(principal)
        return TokenResponse(access_token=token, token_type="bearer", user=principal)

    @staticmethod
    def register(reg_req: RegisterRequest) -> TokenResponse:
        email = reg_req.email.strip()
        existing = RepositoryAdapter.get_candidate_profile(email)
        if existing and existing.get("password_hash"):
            raise ValidationError("A candidate profile with this email already exists.")

        profile_data = {
            "email": email,
            "full_name": reg_req.full_name.strip(),
            "password_hash": hash_password(reg_req.password),
            "skills": [],
            "experience": "",
            "education": "",
            "university": "",
            "phone": "",
            "resume_path": "",
            "resume_filename": "",
        }
        RepositoryAdapter.save_candidate_profile(profile_data, user_id=email)

        principal = UserPrincipal(
            user_id=email,
            email=email,
            full_name=reg_req.full_name.strip(),
            role="candidate",
        )
        token = create_access_token(principal)
        return TokenResponse(access_token=token, token_type="bearer", user=principal)
