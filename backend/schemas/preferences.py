"""User automation preferences schema."""

from pydantic import BaseModel, Field


class UserPreferencesSchema(BaseModel):
    auto_quarantine_enabled: bool = Field(default=False)
    auto_quarantine_threshold: int = Field(default=65, ge=0, le=100)
    auto_apply_enabled: bool = Field(default=False)
    auto_apply_max_risk_score: int = Field(default=45, ge=0, le=100)
    enable_real_smtp_dispatch: bool = Field(default=False)
