"""
User preferences endpoints for automation policies.
"""

from fastapi import APIRouter, Depends
from backend.schemas.preferences import UserPreferencesSchema
from backend.schemas.auth import UserPrincipal
from backend.adapters.repository import RepositoryAdapter
from backend.dependencies import get_current_user

router = APIRouter(prefix="/preferences", tags=["Preferences"])


@router.get("", response_model=UserPreferencesSchema)
async def get_preferences(current_user: UserPrincipal = Depends(get_current_user)):
    prefs = RepositoryAdapter.get_preferences(user_id=current_user.user_id)
    return UserPreferencesSchema(**prefs)


@router.put("", response_model=UserPreferencesSchema)
async def update_preferences(
    prefs: UserPreferencesSchema,
    current_user: UserPrincipal = Depends(get_current_user),
):
    RepositoryAdapter.save_preferences(prefs.model_dump(), user_id=current_user.user_id)
    return prefs
