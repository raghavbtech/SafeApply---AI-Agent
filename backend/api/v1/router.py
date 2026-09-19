"""
V1 API Master Router mounting all sub-routers.
"""

from fastapi import APIRouter
from backend.api.v1.session import router as session_router
from backend.api.v1.emails import router as emails_router
from backend.api.v1.analysis import router as analysis_router
from backend.api.v1.mailbox_actions import router as mailbox_router
from backend.api.v1.verification import router as verification_router
from backend.api.v1.profiles import router as profiles_router
from backend.api.v1.applications import router as applications_router
from backend.api.v1.preferences import router as preferences_router
from backend.api.v1.audit import router as audit_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(session_router)
api_v1_router.include_router(emails_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(mailbox_router)
api_v1_router.include_router(verification_router)
api_v1_router.include_router(profiles_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(preferences_router)
api_v1_router.include_router(audit_router)
