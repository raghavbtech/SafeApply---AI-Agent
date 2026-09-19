"""
System Health and Readiness endpoints.
"""

from fastapi import APIRouter
from backend.adapters.repository import RepositoryAdapter
from backend.adapters.security_engine import SecurityEngineAdapter
from backend.adapters.mail_provider import MailProviderAdapter

router = APIRouter(tags=["Health"])


@router.get("/health/live")
async def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    storage = RepositoryAdapter.get_storage_backend()
    service_health = SecurityEngineAdapter.get_service_health()
    mail_configured = MailProviderAdapter.is_configured()

    return {
        "status": "ready",
        "storage_backend": storage,
        "services": service_health,
        "mail_configured": mail_configured,
    }
