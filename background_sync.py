"""
SafeApply - Background Mailbox Poller
======================================
Runs mail_sync.sync_mailbox_to_db() + auto_scan.scan_all_unscanned()
on a timer, in a daemon thread, so Cosmos DB always holds the latest
recruitment emails without the user manually clicking "Sync".
"""

import os
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Optional

# Ensure standard output and error streams handle Unicode emojis and currency symbols on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from mail_sync import sync_mailbox_to_db, is_mail_configured
from auto_scan import scan_all_unscanned, auto_apply_all_low_risk
from azure_db import DEFAULT_USER_ID, db_set_state

POLL_INTERVAL_SECONDS = int(os.getenv("SAFEAPPLY_POLL_INTERVAL", "10"))  # 10s for ultra-fast response

_poller_thread: Optional[threading.Thread] = None
_lock = threading.Lock()


def is_background_sync_running() -> bool:
    """Check if the background poller daemon is currently active and alive."""
    global _poller_thread
    return bool(_poller_thread and _poller_thread.is_alive())


def _poll_loop(user_id: str):
    print(f"[background_sync] Poller daemon active for {user_id} (interval: {POLL_INTERVAL_SECONDS}s).")
    while True:
        try:
            if is_mail_configured():
                result = sync_mailbox_to_db(user_id=user_id, max_messages=15)
                db_set_state("last_auto_sync", {
                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "result": result,
                }, user_id=user_id)

                if result.get("ok"):
                    # Scan any newly stored or unscanned emails (batch limit 15 for fast response)
                    unscanned_results = scan_all_unscanned(user_id=user_id, limit=15)
                    if unscanned_results:
                        quarantined = sum(1 for r in unscanned_results if r.get("quarantined"))
                        applied = sum(1 for r in unscanned_results if r.get("applied"))
                        print(f"[background_sync] Auto-scanned {len(unscanned_results)} emails (quarantined: {quarantined}, applied: {applied}).")

                    # Note: Automatic job applications require human candidate confirmation
                    # in accordance with Responsible AI principles. Auto-apply is not run silently.
        except Exception as exc:  # noqa: BLE001
            try:
                print(f"[background_sync] poll warning: {repr(exc)}")
            except Exception:
                pass

        time.sleep(POLL_INTERVAL_SECONDS)


def start_background_sync(user_id: str = DEFAULT_USER_ID):
    """Idempotent: safe to call on every Streamlit rerun or FastAPI startup."""
    global _poller_thread
    with _lock:
        if _poller_thread and _poller_thread.is_alive():
            return
        _poller_thread = threading.Thread(target=_poll_loop, args=(user_id,), daemon=True, name="SafeApply-SyncPoller")
        _poller_thread.start()