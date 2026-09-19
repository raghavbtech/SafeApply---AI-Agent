"""
SafeApply - Background Mailbox Poller
======================================
Runs mail_sync.sync_mailbox_to_db() + auto_scan.scan_all_unscanned()
on a timer, in a daemon thread, so Cosmos DB always holds the latest
recruitment emails without the user manually clicking "Sync".
"""

import os
import threading
import time
from datetime import datetime, timezone

from mail_sync import sync_mailbox_to_db, is_mail_configured
from auto_scan import scan_all_unscanned
from azure_db import DEFAULT_USER_ID, db_set_state

POLL_INTERVAL_SECONDS = int(os.getenv("SAFEAPPLY_POLL_INTERVAL", "60"))  # 60s default

_poller_started = False
_lock = threading.Lock()


def is_background_sync_running() -> bool:
    """Check if the background poller daemon is currently active."""
    return _poller_started


def _poll_loop(user_id: str):
    print(f"[background_sync] Poller daemon active for {user_id} (interval: {POLL_INTERVAL_SECONDS}s).")
    while True:
        try:
            if is_mail_configured():
                result = sync_mailbox_to_db(user_id=user_id)
                db_set_state("last_auto_sync", {
                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "result": result,
                }, user_id=user_id)

                if result.get("ok"):
                    # Scan any newly stored or unscanned emails
                    unscanned_results = scan_all_unscanned(user_id=user_id)
                    if unscanned_results:
                        quarantined = sum(1 for r in unscanned_results if r.get("quarantined"))
                        print(f"[background_sync] Auto-scanned {len(unscanned_results)} emails (quarantined: {quarantined}).")
        except Exception as exc:  # noqa: BLE001
            print(f"[background_sync] poll error: {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


def start_background_sync(user_id: str = DEFAULT_USER_ID):
    """Idempotent: safe to call on every Streamlit rerun."""
    global _poller_started
    with _lock:
        if _poller_started:
            return
        thread = threading.Thread(target=_poll_loop, args=(user_id,), daemon=True, name="SafeApply-SyncPoller")
        thread.start()
        _poller_started = True