# SafeApply — complete React + FastAPI migration blueprint

**Baseline:** User-provided `SafeApply---AI-Agent.zip`, inspected 19 September 2026. This document is an implementation specification, not a claim that the migration has already been coded or that live mailbox actions have passed testing. Preserve the original ZIP privately as a rollback source; never publish it because it contains `.env`, user records and cached data.

## 0. Goal and non-negotiable constraints

Replace Streamlit presentation with a dark, neon-inspired React application and introduce FastAPI as the secured orchestration boundary. Retain the Python detection, ML, RAG, Azure services and supported mailbox/application workflows. Do **not** treat replacing Streamlit as permission to remove features or to send applications/move mail merely because a score passes a threshold. Preserve original assessments and distinguish *risk assessment*, *independent verification*, *user decision*, and *external-action outcome*. The ecommerce Dribbble reference is visual inspiration, not an invitation to reuse third-party artwork/assets without permission.

**Architecture:** React/Vite/TypeScript/Tailwind/Motion → authenticated HTTPS `/api/v1` FastAPI → service/adapters → existing Python modules → Azure Cosmos (or explicitly limited local development backend), Azure Search/Language/Foundry, IMAP and SMTP. A separately managed worker performs scheduled sync and controlled background jobs. No browser-held privileged keys or mailbox app passwords. Streamlit stays intact until parity tests pass.

## 1. Findings from the actual ZIP (source of truth)

The ZIP includes `agent.py`, `extractor.py`, `tools.py`, `ml_classifier.py`, `search_indexer.py`, `mail_agent.py`, `mail_sync.py`, `auto_scan.py`, `background_sync.py`, `sync_worker.py`, `azure_db.py`, `database.py`, `security_actions.py`, `job_agent.py`, `app.py`, `ui_mailbox.py`, `test_pipeline.py`, `test_agent_workflow.py`, EDA/training scripts, scam-pattern JSON files and the trained `models/safeapply_classifier.joblib`. It also includes `.env`, `.safeapply_local_db.json`, profile/quarantine JSON, `.git` history, `__pycache__`, and a PDF in `uploads/`. **Never copy these private/runtime items into frontend public assets, a public ZIP, logs, or a Git commit.** Audit Git history and rotate exposed credentials when appropriate. The `.gitignore` exclusion does not untrack previously committed files.

Actual entry points identified in the ZIP:

| Existing module | Existing callables / responsibilities | Migration handling |
|---|---|---|
| `agent.py` | `analyze_job_offer`, `synthesize_with_genai`, `synthesize_fallback`, configuration checks | Wrap analysis; preserve deterministic score and raw evidence; no frontend imports |
| `extractor.py` | `extract_offer_details` and extraction/normalization helpers | Retain behind agent; unit test sender/subject and compensation extraction |
| `tools.py` | `check_red_flags_rag`, `verify_company_domain`, `check_salary_sanity`, `detect_fraud_ml` | Retain and test score contributions and grounded claims |
| `ml_classifier.py` | `load_classifier_artifact`, `predict_job_offer` | Retain model loader; preserve model/version metadata; never execute user-submitted joblib |
| `mail_agent.py` | `is_recruitment_email`, `is_header_definitely_non_recruitment`, `parse_eml_content`, `fetch_live_emails`; `MailboxManager` methods | Keep message parsing/classification and compatibility manager; do not use shared Streamlit state as API source of truth |
| `mail_sync.py` | `get_mail_credentials`, `open_imap`, `close_imap`, `find_junk_folder`, `parse_message`, `sync_mailbox_to_db`, `invalidate_sync_cache` | Mail-provider adapter and background job, bound to authenticated account |
| `auto_scan.py` | `build_analysis_context`, `move_to_spam`, `restore_from_spam`, `apply_to_email`, `auto_apply_all_low_risk`, `scan_and_route_email`, `scan_all_unscanned` | Wrap in authorization, per-user policy and idempotent job service; disable unrestricted auto-apply initially |
| `azure_db.py` | `db_save_emails`, `db_fetch_email`, `db_fetch_all_emails`, `db_update_email_fields`, `db_mailbox_stats`, `db_write_audit`, `db_fetch_audit`, `db_verify_audit_chain`, `db_save_applied_job`, `db_get_applied_jobs`, `db_set_state`, `db_get_state` | Repository adapter; enforce verified user ID and ownership on **every** read/write |
| `database.py` | Legacy/local DB email, quarantine and application methods | Determine callers, designate development-only/legacy; do not run two competing production stores silently |
| `security_actions.py` | `quarantine_email`, `restore_email_from_vault`, `get_quarantined_records`, `generate_verification_checklist` | Preserve local-vault path as distinct from actual IMAP move; expose truthful action outcome |
| `job_agent.py` | `load_candidate_profile`, `save_candidate_profile`, `extract_job_spec`, `evaluate_candidate_match`, `generate_application_package`, `is_no_reply_email`, `revert_back_to_recruiter`, `submit_application`, `load_applied_jobs` | Split preview/approval/send/record; isolate per-user profile and resume; distinguish SMTP delivery from portal submission |
| `background_sync.py`, `sync_worker.py` | Worker startup/sync loops | Run one managed worker per deployment or a queued job system; prevent duplicate processes/sends |
| `app.py`, `ui_mailbox.py` | Streamlit pages, sidebar, inbox/spam UI, session state and user actions | Audit each visible control, map to React/API; keep as fallback until feature parity |
| `test_pipeline.py`, `test_agent_workflow.py` | Existing regression checks | Retain; supplement with API, authorization, mock IMAP/SMTP, frontend and end-to-end tests |

**Existing implementation caveats to address rather than conceal:** `azure_db.py` defaults `SAFEAPPLY_USER_ID` to `demo@safeapply.local`; that is *not authentication*. `auto_scan.py` has automatic application functions and, in this ZIP, default auto-quarantine policy must be audited; `job_agent.py` defaults `ENABLE_REAL_SMTP_DISPATCH` to `true` when unset. Do not expose those defaults in a live multiuser API. `mail_sync.py` uses environment-based IMAP app passwords; account-per-user OAuth/token vault is a future production requirement. A connected mailbox is not equivalent to authentication. The current ZIP is not evidence of tested public deployment or portal-form application.

## 2. Directory and file plan (explicit create/retain/modify)

Keep existing Python files at repo root in the **first migration pass** so imports such as `from agent import ...` remain stable. Do not move the original Python files into `backend/` and break imports while adding FastAPI.

```text
SafeApply---AI-Agent/
├── agent.py, extractor.py, tools.py, ml_classifier.py, search_indexer.py    # RETAIN
├── mail_agent.py, mail_sync.py, auto_scan.py, background_sync.py, sync_worker.py # RETAIN; HARDEN
├── job_agent.py, security_actions.py, azure_db.py, database.py              # RETAIN; ADAPT
├── models/, scam_patterns.json, emscad_scam_patterns.json                  # RETAIN SERVER-SIDE
├── app.py, ui_mailbox.py                                                    # RETAIN until parity
├── backend/                                                                 # CREATE
│   ├── __init__.py
│   ├── main.py                                                               # app factory, middleware, route mounting
│   ├── config.py                                                             # validated env / secure defaults
│   ├── dependencies.py                                                       # authenticated principal, db/services
│   ├── errors.py                                                             # typed errors, safe exception mapping
│   ├── schemas/
│   │   ├── common.py
│   │   ├── emails.py
│   │   ├── analysis.py
│   │   ├── profile.py
│   │   ├── applications.py
│   │   └── settings.py
│   ├── api/v1/
│   │   ├── router.py
│   │   ├── health.py
│   │   ├── auth.py
│   │   ├── emails.py
│   │   ├── analysis.py
│   │   ├── mailbox_actions.py
│   │   ├── verification.py
│   │   ├── profiles.py
│   │   ├── applications.py
│   │   ├── preferences.py
│   │   └── events.py
│   ├── services/
│   │   ├── analysis_service.py
│   │   ├── mailbox_service.py
│   │   ├── action_service.py
│   │   ├── verification_service.py
│   │   ├── profile_service.py
│   │   ├── application_service.py
│   │   └── job_service.py
│   ├── adapters/
│   │   ├── repository.py
│   │   ├── mail_provider.py
│   │   ├── security_engine.py
│   │   └── application_sender.py
│   └── security/
│       ├── identity.py
│       ├── policy.py
│       └── redaction.py
├── frontend/                                                                # CREATE
│   ├── package.json, package-lock.json, index.html, vite.config.ts
│   ├── tsconfig.json, tsconfig.app.json, postcss.config.* , .env.example
│   ├── public/                                                               # NON-SENSITIVE static assets only
│   └── src/
│       ├── main.tsx, App.tsx, index.css
│       ├── theme/tokens.ts
│       ├── api/client.ts, api/contracts.ts
│       ├── api/emails.ts, api/analysis.ts, api/actions.ts, api/jobs.ts
│       ├── auth/AuthProvider.tsx, auth/ProtectedRoute.tsx
│       ├── layouts/AppShell.tsx
│       ├── components/{Sidebar,Header,RiskBadge,ScoreCard,StatusBanner,ConfirmAction,Loading,EmptyState}.tsx
│       ├── pages/{Landing,Dashboard,Inbox,EmailDetail,ManualScan,Analysis,Spam,Verification,JobAgent,Applications,Profile,Settings,Audit,NotFound}.tsx
│       ├── hooks/{useInbox,useAnalysis,useJobStatus}.ts
│       ├── state/selectedEmail.ts
│       └── tests/
├── tests/api/, tests/integration/, tests/security/, tests/fixtures/         # CREATE
├── .env.example, .gitignore, requirements.txt, README.md                    # MODIFY
├── README_MIGRATION.md, docs/API_CONTRACT.md, docs/FEATURE_PARITY.md         # CREATE
└── docker-compose.dev.yml, Dockerfile.api, Dockerfile.worker                 # OPTIONAL deployment stage
```

Do not take the filenames or number of files as a limit: source parity, security and tests determine the final count. Use a lockfile for React dependencies and pin compatible backend versions. Preserve original artifacts and data, not their unsafe storage habits.

## 3. Precise service-to-function connection map

**Do not let FastAPI routes directly run unrestricted mailbox/SMTP side effects.** Route → validate/authenticate → confirm ownership and consent → service → existing function/provider adapter → persist authoritative result → return schema. Existing `DEFAULT_USER_ID` arguments must never be accepted from client request bodies.

| Operation initiated in React | FastAPI service | Existing Python implementation | Main persistence / output |
|---|---|---|---|
| Submit manual offer | `analysis_service.analyze_text` | `agent.analyze_job_offer(text)` | Analysis record, actual score/explanation, provenance |
| Get inbox | `mailbox_service.list_emails` | `azure_db.db_fetch_all_emails(user_id, ...)` | Paginated authenticated user's messages |
| Get email | `mailbox_service.get_email` | `azure_db.db_fetch_email(id, user_id)` | Full parsed sender/subject/body, status |
| Connect mailbox | `mailbox_service.connect_account` | Existing IMAP validation via `mail_sync.open_imap` where applicable | Server-side credential/token reference; connection status only |
| Sync inbox | `job_service.enqueue_sync` | `mail_sync.sync_mailbox_to_db(..., user_id=principal.id)` | Durable sync job, new-message count; polling result |
| Analyze stored email | `analysis_service.analyze_email` | `auto_scan.build_analysis_context` → `agent.analyze_job_offer` or guarded `auto_scan.scan_and_route_email` | Original risk fields retained and versioned |
| Batch scan | `job_service.enqueue_scan` | `auto_scan.scan_all_unscanned(user_id, ...)` after disabling unapproved side effects | Progress, counts and per-message failures |
| Move to actual Junk/Spam | `action_service.move_to_spam` | `auto_scan.move_to_spam(id, user_id)` | Provider-confirmed move result, audit, undo token/state |
| Restore real message | `action_service.restore_email` | `auto_scan.restore_from_spam(id, user_id)` | Provider-confirmed result, audit |
| Quarantine in app only | `action_service.local_quarantine` | `security_actions.quarantine_email` (adapt to user/ownership) | Explicit `local_only=true`; never say mailbox moved |
| Review medium-risk offer | `verification_service.checklist` | `security_actions.generate_verification_checklist` | Checklist, verification observations, user decision separate from score |
| Get/save candidate profile | `profile_service.read/write` | `job_agent.load_candidate_profile/save_candidate_profile` **after per-user refactor** | User-scoped profile/version |
| Upload/remove resume | `profile_service.resume` | Existing candidate-profile/resume lookup to be adapted | Private object, file validation, signed/nonpublic retrieval |
| Extract job and fit | `application_service.preview_job` | `job_agent.extract_job_spec`, `evaluate_candidate_match` | Source-grounded role/skills, gaps, contact confidence |
| Prepare application | `application_service.prepare` | `job_agent.generate_application_package` | Draft only; no mail sent or application marked complete |
| Approve/send email application | `application_service.send_approved` | `job_agent.revert_back_to_recruiter` / `submit_application` after separating dispatch and record paths | Recipient, attachment hash, consent, SMTP result, delivery state |
| Application history | `application_service.history` | `azure_db.db_get_applied_jobs(user_id)` | `draft`, `pending_approval`, `sending`, `sent`, `failed`, `portal_required` etc. |
| Dashboard statistics | `mailbox_service.stats` | `azure_db.db_mailbox_stats(user_id)` plus jobs/apps | Verified counts and freshness timestamps |
| Audit trail | `action_service.audit` | `azure_db.db_fetch_audit/db_verify_audit_chain` | Per-user log; hash chain is not independent external tamper protection |
| Background job state | `job_service.status` | `azure_db.db_get_state/db_set_state` or dedicated durable jobs collection | Job ID, owner, progress, last error and timestamps |

**Compatibility requirement:** Verify the actual function signatures and return values while writing adapters. Some original callables have global JSON/default-user assumptions and should not be passed straight through as public endpoints. `MailboxManager` class methods can remain as legacy compatibility; the database-backed API service is authoritative. Do not double-execute `submit_application` and `revert_back_to_recruiter` if they internally call each other: inspect and test exactly once semantics.

## 4. API contract and response shapes

Prefix all endpoints `/api/v1`. JSON uses UTC ISO-8601 timestamps, opaque identifiers, consistent `snake_case` or deliberately standardized `camelCase` with shared TypeScript schemas, never a mixture. Pagination uses `limit` + opaque cursor. Do not place full raw emails in dashboard list responses.

| Method/path | Request | Response and behavior |
|---|---|---|
| `GET /health/live` | none | Liveness only, no private config |
| `GET /health/ready` | none | Dependency readiness (no secret values) |
| `GET /api/v1/me` | authenticated session | Safe principal/profile summary |
| `GET /api/v1/dashboard` | filters | Counts, connection health, recent items and freshness |
| `GET /api/v1/mailboxes` | none | Connected account descriptors, **no credentials** |
| `POST /api/v1/mailboxes/connect` | OAuth code or explicitly dev-only secure connection setup | Account binding + status; never log tokens/passwords |
| `DELETE /api/v1/mailboxes/{account_id}` | confirm | Revoke/disconnect, stop future worker access |
| `POST /api/v1/mailboxes/{account_id}/sync` | scan window/options | `202 {job_id,status}`; avoid long synchronous HTTP waits |
| `GET /api/v1/emails` | folder, risk, status, search, cursor | Paginated metadata summary |
| `GET /api/v1/emails/{email_id}` | none | Authorized message detail, provider/account ID |
| `POST /api/v1/emails/import-eml` | bounded MIME upload | Parsed draft/message ID and classification |
| `POST /api/v1/analysis/text` | `{text,source?}` | Risk result and provenance, no unrelated user data |
| `POST /api/v1/emails/{email_id}/analyze` | expected version | `202 job_id` or result; dedupe concurrent analysis |
| `GET /api/v1/emails/{email_id}/analysis` | none | Score, level, flags, explanation, tool evidence, model/rules version |
| `POST /api/v1/emails/{email_id}/verification` | checklist updates | User observations and review status; unchanged engine score |
| `POST /api/v1/emails/{email_id}/spam` | `{confirmation,idempotency_key}` | Confirmed IMAP move, or explicit failure/local-only state |
| `POST /api/v1/emails/{email_id}/restore` | confirmation | Provider-confirmed restoration |
| `GET /api/v1/profile`, `PUT /api/v1/profile` | validated profile | Current user's profile only |
| `POST /api/v1/profile/resume` | PDF bounded upload | Private resume ID/hash/status; never public URL |
| `GET /api/v1/jobs/{email_id}/preview` | none | Grounded extracted role/requirements/match; unknown stays unknown |
| `POST /api/v1/jobs/{email_id}/draft` | preferences | Saved draft; **no send** |
| `POST /api/v1/jobs/{email_id}/send` | approved draft revision, exact recipient, resume ID, idempotency key | Durable send job; actual SMTP outcome reported |
| `GET /api/v1/applications` | cursor/status | User-specific application history |
| `GET /api/v1/jobs/runs/{job_id}` | none | Owned job state/progress/failure |
| `GET/PUT /api/v1/preferences` | user opt-in preferences | No implicit auto-send from risk tier alone |
| `GET /api/v1/audit` | filters/cursor | Own action history, no secrets |

Example risk response contract (illustrative field names; **adapt to real `analyze_job_offer` return keys**):

```json
{
  "analysis_id": "opaque-id",
  "email_id": "opaque-email-id-or-null",
  "risk_score": 57,
  "risk_level": "Medium",
  "explanation": "Grounded explanation from current evidence.",
  "identified_red_flags": [],
  "observed_evidence": [],
  "tool_results": {"domain": {}, "salary": {}, "ml": {}, "rag": []},
  "analysis_version": "rules-model-version",
  "review_status": "unreviewed",
  "created_at": "2026-09-19T00:00:00Z"
}
```

Use `400` invalid input, `401` unauthenticated, `403` forbidden, `404` nonexistent *or inaccessible* records, `409` stale version/idempotency conflict, `413` oversized upload, `422` schema validation, `429` throttled, `502/503` provider outage. Never return Python tracebacks, raw tokens, or full LLM prompt to the client. Provide `request_id` and safe error text.

## 5. Complete user journeys and UX state transitions

### A. Sign in and connect mailbox

Unauthenticated visitor → marketing/landing page → sign-in → authenticated dashboard → mailbox connection consent → validate provider access → store only secret reference/token server-side → sync job → status `disconnected/connecting/connected/degraded/error` and last sync time. An IMAP app password in a shared global `.env` is development-only, cannot be assumed to represent every signed-in user. Prefer OAuth for Gmail/Outlook in production; if unsupported at first, explicitly ship a **single-user local-demo mode**, not a misleading multi-user public release.

### B. Manual scan and `.eml` scan

Paste text or upload `.eml` → input size/MIME checks → display original material → analysis service → actual risk score/explanation/evidence/tool status → user can save or discard. For `.eml`, preserve sender, reply-to, subject, visible text and link destinations separately; HTML-to-text parsing must not erase `href` mismatch. Do not execute email HTML, scripts or attachments in the browser. Do not classify a safe-looking message as verified authentic solely from a Low score.

### C. Inbox ingestion / analysis

Worker sync → stable provider account + mailbox UIDVALIDITY + UID / message ID deduplication → classify recruitment intent → persist message → queue analysis → render `unscanned/scanning/scanned/error`; evidence-specific `Low/Medium/High/Critical` only if supported by existing score tier → retain original result and revision. Show manual retry and actual provider errors; don't let frontend polling trigger duplicate scans.

### D. Security routing

High-risk result → risk explanation and observed evidence → show `Move to Spam` (confirmation) or policy-controlled automatic route (opted in) → backend checks actual ownership and provider UID/folder mapping → perform one real move → store provider success/failure. If unable to move, label `Quarantined in SafeApply only` **only when local vault action really occurred**. Restore should resolve updated folder UID and report failure truthfully. Avoid deleting unrelated messages during COPY + Deleted + EXPUNGE fallback; use UID expunge/isolated mailbox behavior where supported, and integration-test with provider sandboxes.

### E. Verification

Medium/uncertain → independently verify via official careers site and university placement office → record factual findings/source/date and user decision → keep unchanged `original_risk_score`, `original_risk_level` and append `review_status`, `user_decision`, `review_evidence`. No `verified` flag from clicking a button alone; no irreversible score overwrite.

### F. Application journey

Eligible message → source-grounded job specification → identify missing requirements without invented defaults → compare user profile → draft email/cover letter/resume selection → preview *exact* recipient, subject, body, attachments and employer verification state → user approves → server validates unchanged draft revision and idempotency → SMTP send → record `sent` only after confirmed SMTP acceptance; otherwise `failed`/`unknown` (avoid automatic retries of an uncertain send). Show `No-reply/portal required` instead of sending when target cannot accept replies. Actual external website submission is **not implemented merely by sending email**; mark as `portal_required` unless separately integrated and confirmed.

### G. Background sync and closing browser

Sync worker runs independent of React/browser session; backend persists job status, last successful checkpoint, errors, and per-mailbox scheduler lease. `GET jobs/{id}` or authenticated SSE communicates status. Only one active worker lease per account and action idempotency key. Disconnecting a mailbox cancels future work and revokes access. Deploy API and worker separately; do not start polling loops from every FastAPI worker process.

## 6. Authentication, privacy and security gates

- Bind `principal.user_id` to validated identity from a trusted auth provider/session, never `X-User-ID` supplied by the browser. Enforce ownership checks on email IDs, IMAP account IDs, resumes, jobs, app records, preference records and audit history. Use session cookies with `HttpOnly`, `Secure`, appropriate `SameSite` and CSRF protection for cookie-authenticated writes, or a properly validated token flow; configure exact-origin CORS.
- No Azure/Search/Foundry, Cosmos, IMAP, SMTP, OAuth refresh, or GitHub secrets in Vite `VITE_*` variables, frontend source, JS bundle, returned API JSON or logs. `VITE_API_BASE_URL` is a public endpoint only. Separate per-account mailbox tokens in a server-side secret store; encrypt and rotate. Never expose `.env` via static hosting.
- Apply rate limiting, payload limits, upload type/magic-byte checks, antivirus scanning as appropriate, strict resume handling, encrypted storage and retention/deletion controls. Log only redacted identifiers; email body/resume and personal contact details are sensitive.
- Secure external actions: explicit informed approval of each SMTP send and attachment; default `ENABLE_REAL_SMTP_DISPATCH=false`, `AUTO_APPLY_ENABLED=false`, `AUTO_QUARANTINE_ENABLED=false` in production until separate reviewed opt-in is implemented. Make low-risk eligibility insufficient as sole send authorization. Protect against prompt injection in email content; model text never grants privileges or changes authorization policy.
- Build verifiable idempotency for `send`, `move`, `restore`, and `sync`. Persist approval record, message/attachment version/hash, provider message ID/UID and result. Resolve partial failures carefully; do not blindly retry uncertain SMTP sends.
- Independent identity, mailbox permission and action approval are separate concepts. Do not claim current `SAFEAPPLY_USER_ID` partitioning means authenticated user isolation.

## 7. Backend data models and lifecycle

Define explicit models and document their invariants before route implementation:

`User` (trusted identity); `MailboxConnection` (owner/provider/account/folder/token-reference/status); `Email` (opaque ID, owner, account, UIDVALIDITY/UID, RFC Message-ID, sender/reply-to/subject/body, classifier status, original folder, live folder, updated provider UID); `Analysis` (immutable revision, extraction, exact observed evidence, ML/RAG/tool outputs, score/level, version, timestamp); `VerificationReview` (reviewer, sourced observations, user decision, analysis link); `ActionRequest` (action, actor, approved target/draft version, idempotency key); `ActionOutcome` (provider result, local-only distinction, errors, audit ID); `CandidateProfile` (owner, skills/education, privacy flags); `Resume` (owner, private blob/hash/type); `ApplicationDraft` (recipient, content, resume references, version, approval); `ApplicationRecord` (channel, send state, provider confirmation); `BackgroundJob` (owner, kind, progress, lease, error, timestamps); `UserPreferences` (separate per-action opt-ins).

Storage: add schema version/migration, uniqueness per user+account+UIDVALIDITY+UID and provider Message-ID fallback, concurrency tokens/ETags, archival and delete policy. Existing JSON and Cosmos structures require an explicit mapping/one-time migration, not blind replacement. Decide one authoritative production store; optional local fallback must be explicit in development and must never silently replace Cosmos in production. Reconcile `database.py`, `azure_db.py` and `security_actions.py` historical JSON vault to avoid divergent records.

## 8. Frontend visual and interaction specification

Visual direction: dark charcoal/navy background, restrained violet/cyan/magenta neon accents, high-contrast text, soft glow only for active actions, large expressive headings, subtle gradients, gentle motion; preserve a serious security-tool character. Responsive desktop sidebar → compact mobile navigation; keyboard-focus styles, screen-reader labels, reduced-motion mode, sensible contrast. Do not use risk-color as the only signal. Use licensed/self-made graphics rather than copying design-reference assets.

Required pages / parity: `Landing`, `Dashboard`, `Inbox`, `EmailDetail`, `ManualScan` (paste+EML), `Analysis`, `Spam` + restore, `Verification`, `JobAgent` (extract/match/draft/approve/send), `Applications`, `Profile` + private resume, `Settings` (connections and separate automation toggles), `Audit`, `NotFound` + authenticated error screen. Account connection and mailbox state always visible. Show provider failures and distinguish `previewed`, `saved`, `queued`, `sent`, `moved` states. No decorative controls: every button executes a real authorized API action or is visibly disabled with explanation.

React implementation: React Router for navigation, TanStack Query for server state/caching/polling, typed API client with centralized error handling and request IDs, React Hook Form + schema validation where helpful, Tailwind design tokens and Motion for animation, Lucide iconography, Playwright for E2E. The browser is a view/controller; mailbox credentials, scores, persistent email bodies and side-effect state remain on the backend. Never derive risk score in UI from its own weights.

## 9. Delivery stages: each must be complete before proceeding

| Stage | Output | Exit criteria |
|---|---|---|
| 0. Secure baseline | Sanitized repo, env example, frozen original tests, secrets review, documented original UI actions | No user data/secrets included in tracked frontend assets; baseline behavior recorded |
| 1. Python adapters | Existing functions wrapped, storage and mail/action boundaries explicit | Legacy pipeline tests pass unchanged; no external action in mock tests |
| 2. FastAPI foundation | Config/auth, schemas, centralized errors, `/health`, analysis/manual scan | OpenAPI schemas correct; malformed/unauthorized requests rejected |
| 3. Mailbox APIs | Authenticated list/detail/connect/sync/scan + jobs | Per-user isolation tests, stable message ID tests, no duplicate sync jobs |
| 4. Security/verification APIs | Evidence/review, explicit real-spam vs local-vault actions, restore + audit | Wrong-user and wrong-UID actions rejected; mock provider success/failure tested |
| 5. Job/profile APIs | Private profile/resume, match, draft, explicit approved SMTP send, history | SMTP called only on authorized reviewed action; retry cannot double-send |
| 6. React shell/theme | Vite/React/Tailwind/Motion, nav, responsive/accessibility patterns | No secrets in built bundle; keyboard/mobile layouts pass |
| 7. Full UI parity | Every current Streamlit interaction connected to API, loading/error/empty states | Feature parity checklist fully signed off with screenshots/flow tests |
| 8. Deployment and cutover | API+worker deployment, HTTPS, CORS, secrets store, monitoring, rollback | Canary with test mailbox; live actions deliberately opted in; rollback tested |

**Feature-parity audit method:** In `app.py` and `ui_mailbox.py`, inventory every `st.button`, `st.form`, `st.file_uploader`, `st.text_area`, navigation tab, status filter, refresh, sync toggle, spinner and state mutation. For each create a row in `docs/FEATURE_PARITY.md`: legacy screen/control → source callable → API route → React component → permission/side effect → automated test → status. Do not declare migration complete while any active legacy control lacks an explicit resolution.

## 10. Test matrix and validation commands

Test tiers: (1) unit tests for extraction/negation/score grounding and role/skill claims; (2) FastAPI TestClient schemas/auth/ownership; (3) mock IMAP UID move/restore/folder errors, fake SMTP recipient/attachment/consent/idempotency, Cosmos repository mocks; (4) frontend component and Playwright user journeys; (5) opt-in sandbox mailbox end-to-end; (6) security tests cross-user IDOR, CSRF/CORS, upload validation and prompt injection; (7) performance: large mailbox pagination, concurrent scan, worker restart; (8) regression comparing new analysis with legacy on identical source inputs. Confirm no external mail changes occur in default development test runs.

Suggested local commands **after project files exist**:

```powershell
# repository root; create a fresh Python environment, install pinned requirements
python -m pytest -q
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# separate terminal
cd frontend
npm ci
npm run dev
npm run build
npm run test
# after Playwright installation
npx playwright test
```

Use `/api/v1` proxy in Vite locally, or exact CORS origin `http://localhost:5173`; never use wildcard CORS with cookies. Test from both desktop and mobile layouts. Failure of an Azure integration must show degraded/error status, not invented analysis evidence or silently claim a live scan succeeded.

## 11. Release blockers / acceptance checklist

- [ ] All existing Streamlit **user-visible** features inventoried, replicated, tested, or explicitly deprecated with user approval.
- [ ] Core original analysis runs identically when given the same input; score remains server-authoritative, model/source versions recorded.
- [ ] Manual offer, `.eml`, stored inbox, sync, batch analysis, risk detail and evidence grounding work.
- [ ] Inbox/Spam/verification/application history persist across reload and worker restarts.
- [ ] Real spam move and local quarantine have distinct verified outcomes; restore handles changed provider UID.
- [ ] No automatic mailbox move or SMTP send without independently recorded user opt-in/approval policy.
- [ ] SMTP delivery and external portal submission are never represented as the same operation.
- [ ] Every user resource has server-side ownership checks; authenticated account-to-mailbox binding tested.
- [ ] Background worker cannot create duplicate scans, email sends or action writes across process restarts.
- [ ] Private uploads/resumes, `.env`, credentials and local snapshots not tracked or served publicly; audit prior publication/history.
- [ ] API error handling, rate limits, logs redaction, CORS, CSRF and secret management validated.
- [ ] Mobile, accessibility, empty/loading/error states and reduced-motion visual checks pass.
- [ ] Unit, API, mock-provider, E2E and limited sandbox live tests pass; documented deployment and rollback available.

## 12. Implementation protocol for file-by-file delivery in VS Code

For every delivery batch, specify **CREATE / MODIFY / RETAIN / REMOVE AFTER CUTOVER**, exact repo-relative path, complete file text, required dependencies and environment variables, commands to run, expected behavior, and automated tests. Never provide a stub advertised as fully integrated; mark placeholder functionality clearly. Implement adapters from inspected callable signatures and run tests before integrating an endpoint. Develop on a feature branch; commit after each passing stage; never force-push teammates' work without agreement. Do not delete Streamlit until both feature parity and production readiness checks succeed.

### Known limits of this blueprint

This blueprint inventories the uploaded archive and identifies the integration contracts, risk gates, files, and testing needed for full feature parity. The exact current JSON keys for every nested existing return value and all individual Streamlit widget handlers require a mechanical source audit while implementing, as described in Stages 0–1. Likewise, Gmail/Outlook OAuth, verified multitenant identity and arbitrary external portal-form submission are **new capabilities**, not features proven to exist in the ZIP. They must not be promised as already working. A comprehensive plan cannot substitute for actual integration tests with the intended Azure environment and test mailbox.

## 13. IDE agent execution contract (read before making edits)

This blueprint is an **outcome specification**, not an instruction to invent a new implementation in place of functioning code. The IDE has access to the live workspace; its checked-out source files, actual signatures, configuration, and tests are authoritative if they differ from the snapshot documented above. Document differences first. Complete the work in the repository rather than merely generating another plan. Do not claim any feature is functional until the relevant tests and, where required, opt-in integration verification pass.

### 13.1 Baseline and discovery

1. Confirm repository root, branch, Git status and active entry points. Create a feature branch; preserve uncommitted user changes. Never reset or force-push a shared branch.
2. Examine **all** Streamlit pages and user-visible controls, the agent analysis path, IMAP/SMTP pathways, both database modules, worker startup, profile/resume handling, configuration, existing tests and model files. Identify dead code and inconsistent duplicated paths instead of assuming every apparent module is active.
3. Capture current import/return schemas and baseline test outputs; add a dependency/call graph and real control-to-handler inventory to `docs/FEATURE_PARITY.md`. Record any baseline test failures **before** changing code. Do not use network-backed Azure/mailbox calls as default tests.
4. Enumerate tracked private files without reproducing their contents in logs. Do not print environment variable values, tokens, raw emails, resumes, or full candidate profiles into tool/chat output. Add exclusions and remove tracked private uploads/runtime data safely; removing sensitive data from history or rotating compromised credentials requires a coordinated owner action. Never place `.env` in React or in build artifacts.
5. Record which features are genuinely working, mock/demo-only, environment-dependent, or proposed; never represent a stub as a completed integration.

### 13.2 Architecture and sequencing

- Keep root Python modules importable and operational during the initial cutover. Introduce `backend/` as an adapter/API layer; refactor core files only when a tested integration requirement demands it. Keep the Streamlit implementation and its original commands intact until parity is established.
- Choose **one authoritative user-scoped persistence path** for production. Never silently fall back to a shared local store or the demo user when a production DB/authentication configuration is missing; fail closed with a clear service-unavailable response.
- Choose and document one consistent, proven authentication strategy before exposing private APIs. Do not introduce mock login that impersonates real user isolation. The dev-only single-user mode must be explicit, isolated from production, and marked visibly in UI/docs. Bind authenticated identity to mailbox connections, stored emails, resumes, audit records and background jobs. Never accept `user_id` supplied by a browser as an authorization decision.
- A production multiuser mailbox connection requires an appropriately secured provider authorization and credential/token lifecycle; the snapshot's server-level IMAP app-password setup is **not** a complete multiuser connect flow. Implement a real tested provider-specific connection or explicitly disable/hide that live multiuser UI until supported, while preserving configured local/development mailbox operation.
- Use managed worker processes/jobs for long-running sync and scanning, and durable status reporting. Enforce single logical worker ownership/leases and idempotency for external actions. A React page refresh must not cancel a queued job or trigger an accidental duplicate send.
- First expose reliable FastAPI contracts and write API tests; then implement the React pages against those contracts. Maintain `/api/v1` contract documentation and typed TypeScript request/response definitions from actual Pydantic schemas. Keep risk calculation exclusively server-side.

### 13.3 Required behavior for every existing user journey

1. **Manual scan:** paste offer or upload bounded `.eml` → normalize source metadata → existing analysis exactly once → retain deterministic score, observed evidence, models/tools status → show grounded result and failures. Explicitly disclose when live external verification was not performed.
2. **Mailbox:** choose authorized account → sync provider by stable mailbox-scoped identifier → classify recruitment mail → list/search/filter/paginate inbox and open message → scan individual/batch with provenance and persisted outcome. Preserve unread/ignored/unscanned/scanned distinctions where the current UI supports them.
3. **Risk routing:** show the original untouched score and separate verification/user decisions; provide manual move-to-spam and restoration only for records with a verified provider message identity and authorized mailbox. A local-only quarantine is not a provider move. Never report provider success based solely on a database update.
4. **Application:** extract requirements without fabricating unspecified fields → compare candidate skills → build preview/draft → show exact destination, text, resume attachment and account → require explicit approval of an immutable draft revision → dispatch through an available verified channel **at most once** → persist actual SMTP outcome separately from recruiter response, portal submission and hiring status. A low-risk result is not permission to send.
5. **Background automation:** respect explicit per-user/per-action preferences; default to no destructive side effects or outgoing email. Do not reuse env-provided mailbox credentials as permission for every app user. Report progress, restart/retry safety, and failures honestly.
6. **Settings/profile/audit:** authenticated account connection status, safe per-user preferences, private resume/profile CRUD where present, reversible mailbox actions where supported, review and send audit trails, honest provider limitations, logout/error/empty/loading states.

### 13.4 Non-negotiable security/correctness tests

- Cross-user access attempts on **every** private endpoint, including background job IDs and file URLs, must fail; ensure ownership is checked *after* resolving opaque IDs as well as in the storage query.
- A high-risk false positive cannot move another email; IMAP UID must be scoped to mailbox + folder + UIDVALIDITY and checked just before action. Avoid mailbox-wide EXPUNGE when it could delete unrelated messages; use safe provider-supported move or a selective, verified fallback and test it.
- Sending a draft twice, refreshing the browser, retrying a failed HTTP request or restarting a worker must not send duplicate application emails. Record an idempotency key and durable transition before side effects; when provider outcome is uncertain, display `unknown`/`needs_reconciliation` rather than automatically re-sending.
- Uploaded `.eml`/resume files need size/type limits, safe MIME parsing, secure filename handling, private storage and clear removal behavior. Treat email bodies, URLs and retrieved RAG documents as untrusted content and do not execute their instructions. Avoid rendering raw email HTML without robust sanitization.
- Keep HTTP errors actionable and redact secrets, PII and unnecessary message bodies in logs; do not expose stack traces or API keys to clients. Rate-limit expensive analysis/sync and prohibit untrusted arbitrary provider hosts or filesystem paths.
- Frontend: no secrets in `VITE_*` variables or public assets; no fake data in production dashboards; visible indicators of unavailable provider capabilities; keyboard and mobile usability, contrast and reduced motion. Respect the visual reference's style, not its copyrighted artwork.

### 13.5 Completion and progress-reporting rules

At the end of each implementation stage, deliver: (a) exact files created/modified; (b) APIs and legacy functions integrated; (c) actual test commands and observed results; (d) remaining limitations and required configuration; and (e) next stage. If your environment cannot run a real Azure/IMAP/SMTP check, say so and include reproducible opt-in verification steps; never infer success from mocks alone. Do not silently omit controls or change feature semantics. Where an essential production dependency (e.g., OAuth application registration, live Azure credentials) is absent, implement a safe disabled/development path and call out the blocker rather than fabricating live behavior.

**Definition of done:** Every existing Streamlit control has a documented disposition and a connected React/API equivalent or explicitly agreed removal; safe core analysis and provider-mocked workflows pass; private data/credentials are protected; exact external-action outcomes are reported truthfully; typecheck, lint, backend tests, frontend build and applicable E2E tests pass; deployment/rollback commands and configuration examples are documented. The user may continue to run the old Streamlit version until they approve cutover. Do not claim perfect functionality or complete live verification without the relevant environment and observed results.
