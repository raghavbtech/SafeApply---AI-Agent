"""
Automated test suite for BlobStorageAdapter, credential encryption, rate limiting, and CSRF protection.
"""

import pytest
from httpx import AsyncClient
from backend.adapters.blob_storage import BlobStorageAdapter
from backend.adapters.mail_provider import encrypt_credential, decrypt_credential, MailProviderAdapter
from backend.security.rate_limiter import SlidingWindowRateLimiter
from backend.security.session import SessionStore
import azure_db


def test_blob_storage_upload_download_delete_cycle():
    """Verify BlobStorageAdapter upload, download, ownership verification, and deletion."""
    user_a = "anon_test_user_alpha_12345"
    user_b = "anon_test_user_bravo_67890"
    content = b"%PDF-1.4 Resume binary data for testing blob adapter."
    filename = "test_resume.pdf"
    content_type = "application/pdf"

    # 1. Upload
    opaque_ref, clean_name = BlobStorageAdapter.upload_resume(
        user_id=user_a, filename=filename, content=content, content_type=content_type
    )
    assert clean_name == "test_resume.pdf"
    assert opaque_ref.startswith(("azure-blob://", "local-blob://"))

    # 2. Download by owner User A
    res_a = BlobStorageAdapter.download_resume(opaque_ref=opaque_ref, user_id=user_a)
    assert res_a is not None
    dl_bytes, dl_fname, dl_type = res_a
    assert dl_bytes == content
    assert dl_fname == "test_resume.pdf"

    # 3. Cross-session access denial: User B attempting to download User A's resume
    res_b = BlobStorageAdapter.download_resume(opaque_ref=opaque_ref, user_id=user_b)
    assert res_b is None, "User B must not be able to download User A's resume blob"

    # 4. Delete
    deleted = BlobStorageAdapter.delete_resume(opaque_ref=opaque_ref, user_id=user_a)
    assert deleted is True

    # 5. Verify deleted
    res_after = BlobStorageAdapter.download_resume(opaque_ref=opaque_ref, user_id=user_a)
    assert res_after is None


def test_mailbox_credential_encryption_and_zero_leakage():
    """Verify credentials are encrypted at rest and never exposed in cleartext."""
    user_id = "anon_mailbox_encryption_test"
    raw_secret = "secret-app-password-xyz-987"

    # Encryption round-trip
    enc = encrypt_credential(raw_secret)
    assert enc != raw_secret
    assert raw_secret not in enc

    dec = decrypt_credential(enc)
    assert dec == raw_secret

    # Connect mailbox via adapter
    MailProviderAdapter.connect_mailbox(
        user_id=user_id,
        creds={
            "provider": "Gmail",
            "username": "candidate.secure@gmail.com",
            "password_or_app_token": raw_secret,
        },
    )

    # Verify connection info returned to callers NEVER includes password
    info = MailProviderAdapter.get_connection_info(user_id=user_id)
    assert info["is_connected"] is True
    assert "password" not in info
    assert "password_or_token" not in info
    assert "encrypted_password_or_token" not in info

    # Inspect persistent state in DB: must be encrypted
    state = azure_db.db_get_state("mailbox_auth", default={}, user_id=user_id)
    assert "encrypted_password_or_token" in state
    assert state.get("password_or_token") is None
    assert state["encrypted_password_or_token"] != raw_secret

    # Disconnect
    MailProviderAdapter.disconnect_mailbox(user_id=user_id)
    info_after = MailProviderAdapter.get_connection_info(user_id=user_id)
    assert info_after["is_connected"] is False


def test_sliding_window_rate_limiter():
    """Verify rate limiter sliding window triggers when request limit is reached."""
    limiter = SlidingWindowRateLimiter()
    key = "test-client-ip-001"

    # Allow up to 3 requests
    allowed_1, _ = limiter.is_allowed(key, max_requests=3, window_seconds=10)
    allowed_2, _ = limiter.is_allowed(key, max_requests=3, window_seconds=10)
    allowed_3, _ = limiter.is_allowed(key, max_requests=3, window_seconds=10)
    assert allowed_1 is True
    assert allowed_2 is True
    assert allowed_3 is True

    # 4th request must be rejected
    allowed_4, wait_sec = limiter.is_allowed(key, max_requests=3, window_seconds=10)
    assert allowed_4 is False
    assert wait_sec > 0


@pytest.mark.asyncio
async def test_csrf_origin_validation(async_client: AsyncClient):
    """Verify CSRF middleware denies cross-site requests with malicious origins."""
    _, token = SessionStore.create_session(user_agent="csrf-test")

    # Request with disallowed malicious origin
    resp_bad = await async_client.post(
        "/api/v1/session/purge",
        cookies={"safeapply_session": token},
        headers={"Origin": "https://malicious-attacker-site.com"},
    )
    assert resp_bad.status_code == 403
    assert "Cross-Site Request Forgery" in resp_bad.json()["error"]["message"]

    # Request with authorized origin
    resp_good = await async_client.post(
        "/api/v1/session/purge",
        cookies={"safeapply_session": token},
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp_good.status_code == 200
