"""
Audit log and cryptographic hash chain verification endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from backend.schemas.audit import AuditChainStatusResponse, AuditRecordSchema
from backend.schemas.auth import UserPrincipal
from backend.services.action_service import ActionService
from backend.dependencies import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=List[AuditRecordSchema])
async def get_audit_trail(current_user: UserPrincipal = Depends(get_current_user)):
    return ActionService.get_audit_trail(user_id=current_user.user_id)


@router.get("/verify", response_model=AuditChainStatusResponse)
async def verify_audit_chain(current_user: UserPrincipal = Depends(get_current_user)):
    return ActionService.verify_audit_chain(user_id=current_user.user_id)
