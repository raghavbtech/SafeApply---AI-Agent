"""
SafeApply Backend Configuration
Validated settings loaded from environment variables with safe production defaults.
"""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "SafeApply API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="SAFEAPPLY_ENV")
    debug: bool = False

    # Security & Anonymous Sessions
    session_secret: str = Field(
        default="safeapply-session-secret-key-change-in-production-32bytes",
        alias="SAFEAPPLY_SESSION_SECRET",
    )
    session_expire_days: int = Field(default=7, alias="SAFEAPPLY_SESSION_EXPIRE_DAYS")
    cookie_name: str = "safeapply_session"
    cookie_secure: bool = Field(default=False, alias="SAFEAPPLY_COOKIE_SECURE")
    cookie_samesite: str = "lax"
    uploads_dir: str = Field(default="uploads", alias="SAFEAPPLY_UPLOADS_DIR")
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        alias="SAFEAPPLY_CORS_ORIGINS",
    )

    # Persistence
    cosmos_endpoint: str = Field(default="", alias="COSMOS_ENDPOINT")
    cosmos_key: str = Field(default="", alias="COSMOS_KEY")
    cosmos_database: str = Field(default="safeapply", alias="COSMOS_DATABASE")
    cosmos_email_container: str = Field(default="emails", alias="COSMOS_EMAIL_CONTAINER")
    cosmos_audit_container: str = Field(default="audit", alias="COSMOS_AUDIT_CONTAINER")
    local_db_path: str = Field(
        default=".safeapply_local_db.json", alias="SAFEAPPLY_LOCAL_DB"
    )

    # Mailbox IMAP / SMTP
    mail_provider: str = Field(default="Gmail", alias="MAIL_PROVIDER")
    mail_username: str = Field(default="", alias="MAIL_USERNAME")
    mail_app_password: str = Field(default="", alias="MAIL_APP_PASSWORD")
    mail_imap_server: str = Field(default="", alias="MAIL_IMAP_SERVER")
    mail_imap_port: int = Field(default=993, alias="MAIL_IMAP_PORT")
    mail_smtp_server: str = Field(default="", alias="MAIL_SMTP_SERVER")

    # Safety Automation Policies - Default FALSE for safety
    auto_quarantine_enabled: bool = Field(
        default=False, alias="AUTO_QUARANTINE_ENABLED"
    )
    auto_quarantine_threshold: int = Field(
        default=65, alias="AUTO_QUARANTINE_THRESHOLD"
    )
    auto_apply_enabled: bool = Field(default=False, alias="AUTO_APPLY_ENABLED")
    auto_apply_max_risk_score: int = Field(
        default=45, alias="AUTO_APPLY_MAX_RISK_SCORE"
    )
    enable_real_smtp_dispatch: bool = Field(
        default=False, alias="ENABLE_REAL_SMTP_DISPATCH"
    )

    # AI Models & Providers
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment_name: str = Field(
        default="gpt-4o-mini", alias="AZURE_OPENAI_DEPLOYMENT_NAME"
    )
    azure_search_endpoint: str = Field(default="", alias="AZURE_SEARCH_ENDPOINT")
    azure_search_key: str = Field(default="", alias="AZURE_SEARCH_KEY")
    azure_language_endpoint: str = Field(default="", alias="AZURE_LANGUAGE_ENDPOINT")
    azure_language_key: str = Field(default="", alias="AZURE_LANGUAGE_KEY")
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    # Background Polling
    poll_interval_seconds: int = Field(default=30, alias="SAFEAPPLY_POLL_INTERVAL")
    sync_fetch_count: int = Field(default=20, alias="SAFEAPPLY_SYNC_FETCH_COUNT")

    @property
    def cors_origins(self) -> List[str]:
        return [
            origin.strip()
            for origin in self.cors_origins_raw.split(",")
            if origin.strip()
        ]


settings = Settings()
