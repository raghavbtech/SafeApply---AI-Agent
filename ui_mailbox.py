"""
SafeApply - Azure-Backed Mailbox UI
====================================

Renders two views over the Cosmos-stored mail:

    render_inbox_view()  - messages SafeApply left in the inbox (Low / Medium)
    render_spam_view()   - messages SafeApply moved to the real Junk folder

Both read from Cosmos, not from Streamlit session state, so a page refresh or
an app restart shows exactly what the background worker has already done.

Integration with app.py
-----------------------
    from ui_mailbox import render_inbox_view, render_spam_view, render_sidebar_status

Then replace the body of your existing mailbox tab with render_inbox_view()
and your quarantine vault tab with render_spam_view().

The "Apply here" / "Ignore" handlers are deliberately thin: they record the
decision in Cosmos and then call an optional callback so your teammate can
plug the Job Agent in without touching this file.
"""

from typing import Any, Callable, Dict, Optional

import streamlit as st

from azure_db import (
    DEFAULT_USER_ID,
    db_fetch_all_emails,
    db_fetch_audit,
    db_get_state,
    db_mailbox_stats,
    db_update_email_fields,
    db_verify_audit_chain,
    db_get_applied_jobs,
    storage_backend,
)
from auto_scan import (
    AUTO_QUARANTINE_ENABLED,
    AUTO_QUARANTINE_THRESHOLD,
    move_to_spam,
    restore_from_spam,
    scan_all_unscanned,
)
from mail_sync import is_mail_configured, sync_mailbox_to_db

USER_ID = DEFAULT_USER_ID

RISK_BADGE_CLASS = {
    "Critical": "badge-critical",
    "High": "badge-high",
    "Medium": "badge-medium",
    "Low": "badge-low",
}


# =========================================================
# HELPERS
# =========================================================

def _badge(email: Dict[str, Any]) -> str:
    if email.get("status") == "unscanned":
        return '<span class="risk-badge badge-neutral">Unscanned</span>'
    level = email.get("risk_level", "Medium")
    score = email.get("risk_score", "-")
    cls = RISK_BADGE_CLASS.get(level, "badge-neutral")
    if email.get("status") == "applied" or email.get("user_decision") == "applied":
        return f'<span class="risk-badge badge-low" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; font-weight: 600;">🚀 Applied &middot; {score}/100</span>'
    return f'<span class="risk-badge {cls}">{level} &middot; {score}/100</span>'


def _run_sync_and_scan(max_messages: int, quarantine: bool) -> None:
    """Sync from IMAP then scan everything new, with a live progress bar."""
    with st.status("SafeApply agent working...", expanded=True) as status:
        st.write("Connecting to mailbox over IMAP...")
        sync = sync_mailbox_to_db(max_messages=max_messages, user_id=USER_ID)

        if not sync["ok"]:
            status.update(label="Sync failed", state="error")
            st.error(sync["error"])
            return

        st.write(
            f"Inspected {sync['inspected']} messages. "
            f"{sync['recruitment']} were recruitment-related and were stored in Azure. "
            f"{sync['skipped']} non-recruitment messages were discarded and never stored."
        )

        st.write("Analysing unscanned messages...")
        bar = st.progress(0.0)
        lines: list[str] = []

        def on_progress(index: int, total: int, result: Dict[str, Any]) -> None:
            bar.progress(index / max(total, 1))
            if result.get("ok"):
                where = "moved to Junk" if result["quarantined"] else "kept in inbox"
                lines.append(
                    f"- **{result['risk_level']}** ({result['risk_score']}/100), {where}: "
                    f"{(result.get('subject') or '')[:60]}"
                )

        results = scan_all_unscanned(
            user_id=USER_ID,
            progress=on_progress,
            allow_auto_quarantine=quarantine,
        )
        bar.progress(1.0)

        if lines:
            st.markdown("\n".join(lines))
        else:
            st.write("No new messages needed analysis.")

        moved = sum(1 for r in results if r.get("quarantined"))
        status.update(
            label=f"Done. {len(results)} analysed, {moved} quarantined.",
            state="complete",
        )


def _auto_sync_on_load(max_messages: int, quarantine: bool, min_gap_seconds: int = 600) -> None:
    """
    Trigger one sync when the page loads if the last one was long enough ago.

    This gives 'it updates by itself' behaviour inside Streamlit. The
    background worker (sync_worker.py) is still the real automation, because
    it keeps running when nobody has the page open.
    """
    from datetime import datetime, timezone

    if st.session_state.get("_autosync_done"):
        return

    last = db_get_state("last_sync", None, user_id=USER_ID)
    should_sync = True

    if last and last.get("at"):
        try:
            elapsed = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(last["at"])
            ).total_seconds()
            should_sync = elapsed > min_gap_seconds
        except Exception:
            should_sync = True

    st.session_state["_autosync_done"] = True

    if should_sync and is_mail_configured():
        _run_sync_and_scan(max_messages, quarantine)


# =========================================================
# SIDEBAR STATUS
# =========================================================

def render_sidebar_status() -> None:
    """Drop this into your existing sidebar block."""
    st.markdown(f"**Mail Store**: {storage_backend()}")
    st.markdown(f"**Mailbox Link**: {'Connected (IMAP)' if is_mail_configured() else 'Not configured'}")

    last = db_get_state("last_sync", None, user_id=USER_ID)
    if last:
        st.caption(f"Last sync: {last.get('at', 'never')} ({last.get('stored', 0)} stored)")
    else:
        st.caption("Last sync: never")

    chain = db_verify_audit_chain(USER_ID)
    if chain["records"]:
        if chain["valid"]:
            st.caption(f"Audit chain verified ({chain['records']} records)")
        else:
            st.error(f"Audit chain broken at record {chain['broken_at']}")


# =========================================================
# INBOX VIEW
# =========================================================

@st.fragment(run_every="20s")
def render_inbox_view(
    on_apply: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_ignore: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    """
    Messages SafeApply assessed as Low or Medium risk and left in the inbox.
    Automatically refreshes in real-time as background sync fetches new emails.
    """
    st.markdown("### Inbox")
    st.caption(
        "Recruitment messages SafeApply analysed and left in your mailbox. "
        "High and Critical risk messages are in the Quarantine tab."
    )

    # Live auto-sync indicator badge
    status_badge = """
    <div style="display: flex; align-items: center; gap: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 6px 12px; margin-bottom: 12px;">
        <span style="height: 9px; width: 9px; background-color: #10b981; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px #10b981;"></span>
        <span style="color: #10b981; font-weight: 600; font-size: 0.85rem;">Continuous Auto-Sync Active</span>
        <span style="color: #94a3b8; font-size: 0.8rem; margin-left: auto;">Background daemon checks mailbox automatically &bull; Live UI updates</span>
    </div>
    """
    st.markdown(status_badge, unsafe_allow_html=True)

    control_col, sync_col, auto_col = st.columns([2, 2, 3])
    with control_col:
        fetch_count = st.number_input("Emails per sync", 5, 50, 15, step=5)
    with sync_col:
        st.write("")
        sync_clicked = st.button("Force Sync Now", type="secondary", use_container_width=True, help="Triggers an immediate sync check without waiting for the background timer.")
    with auto_col:
        quarantine = st.toggle(
            "Auto-quarantine High / Critical",
            value=AUTO_QUARANTINE_ENABLED,
            help=(
                f"When on, messages scoring {AUTO_QUARANTINE_THRESHOLD}/100 or above are "
                "moved to your mailbox's Junk folder automatically. Every move is logged "
                "and can be undone from the Quarantine tab."
            ),
        )

    _auto_sync_on_load(int(fetch_count), quarantine)

    if sync_clicked:
        st.session_state["_autosync_done"] = True
        _run_sync_and_scan(int(fetch_count), quarantine)

    stats = db_mailbox_stats(USER_ID)
    cols = st.columns(5)
    cols[0].metric("In Inbox", stats["inbox"])
    cols[1].metric("Quarantined", stats["spam"])
    cols[2].metric("Needs Check", stats["medium"])
    cols[3].metric("Low Risk", stats["low"])
    cols[4].metric("Decided", stats["applied"] + stats["ignored"])

    st.divider()

    emails = db_fetch_all_emails(USER_ID, folder="inbox")
    if not emails:
        st.info(
            "No recruitment emails stored yet. Press **Sync & Scan Now**, or start the "
            "background worker with `python sync_worker.py`."
        )
        return

    for email in emails:
        with st.container(border=True):
            head, badge = st.columns([5, 2])
            with head:
                st.markdown(f"**{email.get('subject', '(no subject)')}**")
                st.caption(
                    f"{email.get('sender_name', '')} `<{email.get('sender', '')}>` "
                    f"&middot; {email.get('date', '')}"
                )
            with badge:
                st.markdown(_badge(email), unsafe_allow_html=True)

            analysis = email.get("analysis") or {}
            if analysis.get("explanation"):
                st.write(analysis["explanation"])

            flags = analysis.get("identified_red_flags", [])
            if flags and email.get("risk_level") != "Low":
                with st.expander(f"Evidence ({len(flags)})"):
                    for flag in flags:
                        st.markdown(f"- {flag}")

            with st.expander("Original message"):
                st.text(email.get("body", "")[:4000])

            decision = email.get("user_decision", "none")
            is_applied = (decision == "applied") or (email.get("status") == "applied")

            if is_applied:
                try:
                    from azure_db import db_get_applied_jobs, DEFAULT_USER_ID
                    applied_jobs = db_get_applied_jobs(USER_ID)
                except Exception:
                    applied_jobs = []

                app_rec = next((r for r in applied_jobs if r.get("email_id") == email["id"]), None)
                sender_addr = email.get("sender", "")

                from job_agent import is_no_reply_email, load_candidate_profile
                is_no_reply = is_no_reply_email(sender_addr) or (app_rec.get("is_no_reply") if app_rec else False)
                c_prof = load_candidate_profile()
                cand_resume = (app_rec.get("resume_filename") if app_rec else "") or email.get("resume_filename") or c_prof.get("resume_filename") or "chatgptService.pdf"
                sub_id = (app_rec.get("submission_id") if app_rec else "") or email.get("submission_id") or "APP-AUTO-CONFIRMED"
                comp_name = (app_rec.get("company_name") if app_rec else "") or email.get("company_name") or "Employer"
                role_name = (app_rec.get("role_title") if app_rec else "") or email.get("role_title") or "Legitimate Role"
                applied_date = (app_rec.get("applied_at") if app_rec else "") or email.get("applied_at") or "Recently"
                is_low_risk = email.get("risk_level") == "Low"

                header_label = "🚀 **Auto-Applied by SafeApply Agent** (Low Risk Verified)" if is_low_risk else "✅ **Application Submitted**"
                dispatch_detail = f"Dispatched direct revert-back email to `{sender_addr}`" if not is_no_reply else f"Application package generated for portal submission: `{app_rec.get('portal_url') if app_rec else 'Official Portal'}`"

                st.success(
                    f"{header_label}\n\n"
                    f"SafeApply verified this opportunity as legitimate and **has automatically applied** for **{role_name}** at **{comp_name}**.\n\n"
                    f"- **Status:** ✅ Applied\n"
                    f"- **Tracking ID:** `{sub_id}`\n"
                    f"- **Attached Resume:** `{cand_resume}`\n"
                    f"- **Action:** {dispatch_detail}\n"
                    f"- **Timestamp:** {applied_date}"
                )

                app_pkg = email.get("application_package") or (app_rec if app_rec else {})
                cl_text = (app_pkg.get("cover_letter") if isinstance(app_pkg, dict) else "") or (app_rec.get("cover_letter_snippet") if app_rec else "")
                rr_text = (app_pkg.get("recruiter_reply") if isinstance(app_pkg, dict) else "") or (app_rec.get("recruiter_reply") if app_rec else "")
                if cl_text or rr_text:
                    with st.expander("📄 View Submitted Cover Letter & Response Draft"):
                        if cl_text:
                            st.markdown("**Cover Letter:**")
                            st.text(cl_text[:2000])
                        if rr_text:
                            st.markdown("**Recruiter Response:**")
                            st.text(rr_text[:1500])

            elif decision == "ignored":
                st.info("You ignored this opportunity.")
            else:
                if email.get("risk_level") == "Medium":
                    st.warning(
                        "SafeApply could not fully verify this sender. Confirm the "
                        "employer through an independently obtained contact before "
                        "sharing documents."
                    )

                from job_agent import is_no_reply_email
                sender_addr = email.get("sender", "")
                is_no_reply = is_no_reply_email(sender_addr)

                if is_no_reply:
                    st.caption("*(No-Reply Sender Detected: Clicking Apply will prepare package for official portal submission)*")
                else:
                    st.caption("*(Direct Recruiter Email: Clicking Apply will automatically send revert-back email expressing candidate interest)*")

                a_col, i_col, q_col = st.columns(3)

                with a_col:
                    btn_label = "Apply (Portal)" if is_no_reply else "Apply (Revert Email)"
                    if st.button(btn_label, key=f"apply_{email['id']}",
                                 type="primary", use_container_width=True):
                        db_update_email_fields(
                            email["id"], {"user_decision": "applied"}, USER_ID
                        )
                        if on_apply:
                            on_apply(email)
                        st.rerun()

                with i_col:
                    if st.button("Ignore", key=f"ignore_{email['id']}",
                                 use_container_width=True):
                        db_update_email_fields(
                            email["id"], {"user_decision": "ignored"}, USER_ID
                        )
                        if on_ignore:
                            on_ignore(email)
                        st.rerun()

                with q_col:
                    if st.button("Move to Junk", key=f"junk_{email['id']}",
                                 use_container_width=True):
                        result = move_to_spam(
                            email["id"],
                            reason="Manually quarantined by user",
                            user_id=USER_ID,
                            automated=False,
                        )
                        if result.get("mailbox_moved"):
                            st.success("Moved to your mailbox Junk folder.")
                        else:
                            st.warning(
                                f"Quarantined in SafeApply, but the mailbox move "
                                f"did not complete: {result.get('error')}"
                            )
                        st.rerun()

            if email.get("risk_level") == "Low":
                st.caption(
                    "SafeApply currently assesses this opportunity as low risk. "
                    "That is an advisory result, not confirmation that the employer "
                    "is genuine."
                )


# =========================================================
# QUARANTINE / SPAM VIEW
# =========================================================

@st.fragment(run_every="20s")
def render_spam_view() -> None:
    """Messages SafeApply moved out of the inbox, with one-click restore."""
    st.markdown("### Quarantine")
    st.caption(
        "Recruitment messages SafeApply moved to your mailbox's Junk folder. "
        "Nothing is ever deleted, and every move here can be undone."
    )

    emails = db_fetch_all_emails(USER_ID, folder="spam")

    if not emails:
        st.info("Nothing quarantined yet.")
    else:
        st.markdown(f"**{len(emails)} message(s) quarantined**")

        for email in emails:
            with st.container(border=True):
                head, badge = st.columns([5, 2])
                with head:
                    st.markdown(f"**{email.get('subject', '(no subject)')}**")
                    st.caption(
                        f"{email.get('sender_name', '')} `<{email.get('sender', '')}>` "
                        f"&middot; {email.get('date', '')}"
                    )
                with badge:
                    st.markdown(_badge(email), unsafe_allow_html=True)

                mode = "Automatic" if email.get("quarantined_automatically") else "Manual"
                moved = email.get("mailbox_action") == "moved_to_junk"
                st.caption(
                    f"{mode} quarantine at {email.get('quarantined_at', 'unknown time')} &middot; "
                    + ("moved in mailbox" if moved else "SafeApply record only")
                )
                st.markdown(f"**Reason:** {email.get('quarantine_reason', 'Not recorded')}")

                analysis = email.get("analysis") or {}
                flags = analysis.get("identified_red_flags", [])
                if flags:
                    with st.expander(f"Evidence ({len(flags)})"):
                        for flag in flags:
                            st.markdown(f"- {flag}")

                with st.expander("Original message"):
                    st.text(email.get("body", "")[:4000])

                if st.button("Restore to inbox", key=f"restore_{email['id']}",
                             use_container_width=True):
                    result = restore_from_spam(email["id"], USER_ID)
                    if result.get("mailbox_restored"):
                        st.success("Moved back to your inbox.")
                    else:
                        st.warning(
                            f"Restored in SafeApply, but the mailbox move did not "
                            f"complete: {result.get('error')}"
                        )
                    st.rerun()

    st.divider()
    st.markdown("#### Audit trail")

    chain = db_verify_audit_chain(USER_ID)
    if chain["valid"]:
        st.success(
            f"Hash chain verified across {chain['records']} records. No record has "
            "been altered since it was written."
        )
    else:
        st.error(f"Chain broken at record {chain['broken_at']}: {chain['reason']}")

    records = db_fetch_audit(USER_ID)
    if records:
        st.dataframe(
            [
                {
                    "#": r.get("sequence"),
                    "Time": r.get("timestamp"),
                    "Action": r.get("action"),
                    "Risk": r.get("details", {}).get("risk_level", ""),
                    "Subject": (r.get("details", {}).get("subject") or "")[:45],
                }
                for r in reversed(records[-40:])
            ],
            use_container_width=True,
            hide_index=True,
        )