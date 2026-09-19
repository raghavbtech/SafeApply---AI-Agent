"""
Mailbox connection, sync, and spam routing endpoints.
"""

from fastapi import APIRouter, Depends, Query
from backend.schemas.mailbox import (
    ConnectMailboxRequest,
    MailboxConnectionStatus,
    RestoreActionResponse,
    SpamActionRequest,
    SpamActionResponse,
    SyncMailboxRequest,
    SyncMailboxResult,
)
from backend.schemas.auth import UserPrincipal
from backend.services.mailbox_service import MailboxService
from backend.services.action_service import ActionService
from backend.adapters.mail_provider import MailProviderAdapter
from backend.dependencies import get_current_user

router = APIRouter(tags=["Mailbox Actions"])


@router.get("/dashboard")
async def get_dashboard(current_user: UserPrincipal = Depends(get_current_user)):
    return MailboxService.get_dashboard(user_id=current_user.user_id)


@router.get("/mailboxes")
async def get_mailboxes(current_user: UserPrincipal = Depends(get_current_user)):
    info = MailProviderAdapter.get_connection_info(user_id=current_user.user_id)
    return info


@router.post("/mailboxes/connect")
async def connect_mailbox(
    req: ConnectMailboxRequest,
    current_user: UserPrincipal = Depends(get_current_user),
):
    info = MailProviderAdapter.connect_mailbox(user_id=current_user.user_id, creds=req.model_dump())
    return {"success": True, "mailbox": info}


@router.post("/mailboxes/disconnect")
async def disconnect_mailbox(current_user: UserPrincipal = Depends(get_current_user)):
    MailProviderAdapter.disconnect_mailbox(user_id=current_user.user_id)
    return {"success": True, "message": "Mailbox disconnected and credentials removed."}


@router.post("/mailboxes/sync", response_model=SyncMailboxResult)
async def sync_mailbox(
    req: SyncMailboxRequest = SyncMailboxRequest(max_messages=15),
    current_user: UserPrincipal = Depends(get_current_user),
):
    return MailboxService.sync_mailbox(user_id=current_user.user_id, max_messages=req.max_messages)


@router.post("/emails/{email_id}/spam", response_model=SpamActionResponse)
async def move_to_spam(
    email_id: str,
    action_req: SpamActionRequest = SpamActionRequest(),
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ActionService.move_to_spam(
        email_id=email_id, reason=action_req.reason, user_id=current_user.user_id
    )


@router.post("/emails/{email_id}/restore", response_model=RestoreActionResponse)
async def restore_from_spam(
    email_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return ActionService.restore_from_spam(email_id=email_id, user_id=current_user.user_id)
