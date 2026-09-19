# SafeApply — Feature Parity Matrix

This document tracks every user-visible control, workflow, and data view from the original Streamlit application (`app.py` & `ui_mailbox.py`) through to its FastAPI endpoint and React frontend component implementation.

## Consolidated 6-Destination Navigation Map

To ensure optimal usability for students and job seekers, SafeApply consolidates all capabilities into **exactly six primary navigation destinations**:

1. **Dashboard** (`/dashboard`): Real-time threat status, advisory risk distribution, 4 candidate shortcuts (**Scan Job Offer**, **Upload Resume**, **My Mailbox**, **Job Applications**), recent recruitment emails, candidate privacy & session status.
2. **Scan Job Offer** (`/scan`): Ad-hoc offer analysis and `.eml` upload with the 4-pillar detection pipeline, benchmark presets, and contextual next-step advice.
3. **My Mailbox** (`/inbox`): Unified Active Inbox, Quarantined Threats vault tab (with Restore to Inbox and Quarantine audit tracking), and contextual interactive Verification Checklist for ambiguous offers (with Verify & Trust Offer override).
4. **Job Applications** (`/applications`): Combined Opportunities (job extraction & skill overlap), Prepare Application (tailored drafts, cover letters, recruiter replies, and explicit Human-in-the-Loop approval modal), and History (submission tracking).
5. **My Profile** (`/profile`): High-contrast, Poppins-styled candidate details, education, skill badges, target locations, and resume management.
6. **Settings** (`/settings`): Remote mailbox credentials connection/disconnection, autonomous quarantine and auto-apply thresholds, live SMTP dispatch toggle, and "Delete All My Session Data" privacy controls.

---

## Feature Parity Checklist

| # | Legacy Screen / Control | Source Callable / Module | API Route | Consolidated React Page | Side Effect / Permission | Parity Status |
|---|---|---|---|---|---|---|
| 1 | Onboarding Modal (Name, Email, Phone, Edu, Skills, Resume upload) | `job_agent.save_candidate_profile`, `is_candidate_profile_complete` | `GET/PUT /api/v1/profile`, `POST /api/v1/profile/resume` | `Profile.tsx`, `AppShell.tsx` | Optional & dismissible modal; stores candidate profile in session partition | Connected & Tested |
| 2 | Sidebar Service Health (GenAI, RAG, Language, ML, Mail store, Mail link, Audit chain) | `agent.is_azure_openai_configured`, `search_indexer`, `extractor`, `azure_db.storage_backend`, `db_verify_audit_chain` | `GET /health/ready`, `GET /api/v1/audit/verify`, `GET /api/v1/dashboard` | `Dashboard.tsx`, `Header.tsx` | Read-only status aggregation | Connected & Tested |
| 3 | Active Candidate Summary in Sidebar | `job_agent.load_candidate_profile` | `GET /api/v1/profile` | `Sidebar.tsx`, `Header.tsx` | Read-only; shows Anonymous Visitor if unconfigured | Connected & Tested |
| 4 | Mailbox Metrics Bar (In Inbox, Quarantined, Needs Check, Low Risk, Decided) | `azure_db.db_mailbox_stats` | `GET /api/v1/dashboard` | `Dashboard.tsx`, `Inbox.tsx` | Read-only stats | Connected & Tested |
| 5 | Sync Now / Force Sync button | `mail_sync.sync_mailbox_to_db` | `POST /api/v1/mailboxes/sync` | `Inbox.tsx`, `Settings.tsx` | Enqueues background IMAP sync job | Connected & Tested |
| 6 | Auto-quarantine Toggle | `auto_scan.AUTO_QUARANTINE_ENABLED` | `GET/PUT /api/v1/preferences` | `Settings.tsx`, `Inbox.tsx` | User automation policy | Connected & Tested |
| 7 | Inbox Messages Filter (All, Unscanned, High Risk, Ambiguous, Legit, Quarantined, Applied) | `azure_db.db_fetch_all_emails` (filter parameters) | `GET /api/v1/emails?folder=inbox&risk_level=...&status=...` | `Inbox.tsx` | Filtered query | Connected & Tested |
| 8 | Email Card / Summary View | `ui_mailbox._badge`, subject, sender, date, risk score | `GET /api/v1/emails` | `Inbox.tsx`, `ScoreCard.tsx`, `RiskBadge.tsx` | Read-only listing | Connected & Tested |
| 9 | Email Dossier View (Subject, Sender, Date, Body, Claimed Company) | `azure_db.db_fetch_email` | `GET /api/v1/emails/{id}` | `Inbox.tsx` (Right Pane) | Read-only message detail | Connected & Tested |
| 10 | 4-Pillar Security Analysis Breakdown (Rules, EMSCAD ML, Azure Search RAG, Domain/Salary) | `agent.analyze_job_offer`, `tools.*` | `GET /api/v1/emails/{id}/analysis`, `POST /api/v1/emails/{id}/analyze` | `Inbox.tsx`, `Analysis.tsx` | Runs deterministic + ML + RAG analysis | Connected & Tested |
| 11 | Move to Junk / Spam button | `auto_scan.move_to_spam` | `POST /api/v1/emails/{id}/spam` | `Inbox.tsx` | IMAP move + audit record | Connected & Tested |
| 12 | Restore to Inbox button | `auto_scan.restore_from_spam` | `POST /api/v1/emails/{id}/restore` | `Inbox.tsx` (Quarantined Threats Tab) | IMAP restore to INBOX + audit record | Connected & Tested |
| 13 | Medium-Risk Verification Checklist (Domain, HR contact, No fee policy, Placement cell) | `security_actions.generate_verification_checklist` | `GET /api/v1/emails/{id}/verification`, `POST /api/v1/emails/{id}/verification` | `Inbox.tsx` (Contextual Checklist) | Records user review observations; preserves original score | Connected & Tested |
| 14 | Candidate Verification Override button | `ui_mailbox.py` lines 869-878 (`user_override`) | `POST /api/v1/emails/{id}/verification` (`override=True`) | `Inbox.tsx` (Verify & Trust Offer) | Records trusted candidate override in audit log | Connected & Tested |
| 15 | Legitimate Job Match Evaluation (Skill overlap %, matched skills, missing skills) | `job_agent.extract_job_spec`, `job_agent.evaluate_candidate_match` | `GET /api/v1/jobs/{id}/preview` | `Applications.tsx` (Opportunities Tab) | Grounded extraction and matching against uploaded profile | Connected & Tested |
| 16 | AI Application Package Generation (Tailored Cover Letter, Recruiter Reply, Talking Points) | `job_agent.generate_application_package` | `POST /api/v1/jobs/{id}/draft` | `Applications.tsx` (Prepare Application Tab) | GenAI / template generation (editable preview) | Connected & Tested |
| 17 | Approve & Send Application (SMTP dispatch or Portal required) | `job_agent.submit_application`, `revert_back_to_recruiter` | `POST /api/v1/jobs/{id}/send` | `Applications.tsx` (Approval Modal) | Explicit user approved send; records application | Connected & Tested |
| 18 | Applied Jobs Tracker | `azure_db.db_get_applied_jobs` | `GET /api/v1/applications` | `Applications.tsx` (History Tab) | Read-only application history | Connected & Tested |
| 19 | Ad-Hoc Text Analyzer with Preset Samples | `agent.analyze_job_offer`, `app.py:PRESET_SAMPLES` | `POST /api/v1/analysis/text` | `ManualScan.tsx` | In-memory text analysis; accessible without login or onboarding | Connected & Tested |
| 20 | EML File Upload & Ingestion | `mail_agent.parse_eml_content`, `mail_sync.make_email_doc_id` | `POST /api/v1/emails/import-eml` | `ManualScan.tsx`, `Inbox.tsx` | MIME parser, recruitment classification, doc storage | Connected & Tested |
| 21 | Quarantined Threat Vault with Indicators | `security_actions.get_quarantined_records` | `GET /api/v1/emails?folder=spam` | `Inbox.tsx` (Quarantined Threats Tab) | Read-only spam list with restore action | Connected & Tested |
| 22 | Cryptographic Audit Trail & Hash Chain Verification | `azure_db.db_fetch_audit`, `azure_db.db_verify_audit_chain` | `GET /api/v1/audit`, `GET /api/v1/audit/verify` | `Dashboard.tsx`, `Settings.tsx` | Cryptographic SHA-256 chain verification | Connected & Tested |
| 23 | Responsible AI Disclaimers & Advice | `agent.RESPONSIBLE_AI_DISCLAIMER` | Embedded in contracts | `AppShell.tsx`, `Dashboard.tsx` | Advisory guidance display | Connected & Tested |
| 24 | Delete My Data / Session Purge | `azure_db.db_purge_user_data`, `ProfileService.delete_profile` | `DELETE /api/v1/session/data` | `Header.tsx`, `Settings.tsx` | Purges Cosmos DB partition, local DB, disk resume files | Connected & Tested |
| 25 | Per-Session Mailbox Connect / Disconnect | `MailProviderAdapter.connect_mailbox`, `disconnect_mailbox` | `POST /api/v1/mailboxes/connect`, `POST /api/v1/mailboxes/disconnect` | `Settings.tsx` | Isolated session-scoped IMAP credentials | Connected & Tested |
