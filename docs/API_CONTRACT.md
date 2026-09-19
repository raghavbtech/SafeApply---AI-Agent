# SafeApply — API Contract Specification

All API endpoints are mounted under `/api/v1` (with system health endpoints under `/health`).
Timestamps are UTC ISO-8601 strings. Identifiers are opaque strings. Authentication and session tracking are handled seamlessly via unpredictable server-side anonymous visitor sessions delivered through HTTP-only cookies (`safeapply_session`) or `Authorization: Bearer <session_token>`.

---

## Architecture Summary: Zero-Account Public Model

SafeApply operates as a 100% public, account-free web application:
- **No Login / No Signup**: Visitors are never prompted for usernames, passwords, or OAuth logins.
- **Anonymous Sessions**: On the first request to any endpoint, a cryptographically secure random session is generated (`anon_<uuid>`). The raw token is delivered via an HTTP-only, SameSite cookie, and only its SHA-256 hash is retained on the server.
- **Partitioned Data Isolation**: Cosmos DB `/user_id` partition keys and local database state use `session_id`. Visitor A can never inspect or alter Visitor B's profile, resume, emails, or applications.
- **Durable Azure Blob Storage for Resumes**: Resume files are stored securely in private Azure Blob Storage (or session-isolated local storage fallback). Resumes are downloaded as streaming byte responses; storage paths and access keys are never exposed to clients.
- **Mailbox Credential Encryption at Rest**: IMAP/SMTP credentials are encrypted via Fernet/authenticated cipher stream before persistence in Cosmos DB or local state. Passwords and app tokens are never returned in responses.
- **Abuse & DoS Controls**: In-memory sliding-window rate limiters protect sensitive endpoints (threat analysis, resume upload, application dispatch, mailbox sync).
- **CSRF Protection**: State-changing cookie-authenticated requests enforce strict `Origin` / `Referer` validation against allowed CORS origins.
- **Frictionless Scanner Access**: Visitors can immediately use `/scan`, `/dashboard`, `/inbox`, `/quarantine`, and `/audit` without completing candidate onboarding.
- **Candidate Privacy & Complete Data Erasure**: Visitors can trigger "Delete My Data" at any time to purge their profile, blob-stored resume, imported emails, encrypted mailbox credentials, and cryptographic audit records.

---

## Endpoints Inventory

### System Health
- `GET /health/live`: Basic liveness check.
- `GET /health/ready`: Readiness check testing connectivity to storage (Cosmos/Local DB), Azure AI services, and mailbox configuration.

### Anonymous Visitor Session & Data Privacy
- `GET /api/v1/session`: Initialize or retrieve current anonymous visitor session. Returns session ID, creation timestamp, profile status, and isolation mode.
- `DELETE /api/v1/session/data`: **Delete My Data** — Permanently purges all database records, disk-stored resume files, imported emails, job applications, mailbox credentials, and audit logs belonging to this visitor session.
- `POST /api/v1/session/purge`: Backward-compatible alias for complete data erasure.

### Dashboard & Metrics
- `GET /api/v1/dashboard`: Summary statistics (inbox, spam, unscanned, critical, high, medium, low, applied), recent alerts, and system health status.

### Threat Analysis (4-Pillar Detection Engine)
- `POST /api/v1/analysis/text`: Direct 4-pillar analysis on arbitrary recruitment text (presets or custom user input). No profile or resume required.
- `POST /api/v1/emails/{id}/analyze`: Trigger 4-pillar analysis on an ingested email.
- `GET /api/v1/emails/{id}/analysis`: Retrieve cached 4-pillar analysis results (Rules, EMSCAD ML, Azure Search RAG, Domain/Salary heuristics).

### Emails & Ingestion
- `GET /api/v1/emails`: List stored recruitment emails with filtering (`folder`, `status`, `risk_level`, `search`) and pagination.
- `GET /api/v1/emails/{id}`: Detailed email view with full body, sender headers, metadata, and risk analysis.
- `POST /api/v1/emails/import-eml`: Upload MIME `.eml` file; parses headers/body, determines recruitment status, stores email in session partition.
- `POST /api/v1/emails/batch-scan`: Run security scan across all unscanned emails in the visitor's inbox.

### Mailbox Management (Per-Session Isolation)
- `GET /api/v1/mailboxes`: Get connected mailbox status for the current session (credentials are never exposed).
- `POST /api/v1/mailboxes/connect`: Connect personal IMAP mailbox credentials (`provider`, `username`, `password_or_app_token`, `imap_server`, `imap_port`) scoped strictly to this visitor.
- `POST /api/v1/mailboxes/disconnect`: Disconnect personal IMAP mailbox and delete stored credentials for this session.
- `POST /api/v1/mailboxes/sync`: Trigger asynchronous IMAP mailbox sync and inbox ingestion for the connected mailbox.
- `POST /api/v1/emails/{id}/spam`: Move email to spam/junk folder (IMAP move + quarantine vault audit record).
- `POST /api/v1/emails/{id}/restore`: Restore email from spam folder back to inbox.

### Verification (Medium-Risk Ambiguous Offers)
- `GET /api/v1/emails/{id}/verification`: Retrieve interactive verification checklist tailored to the email's ambiguous signals.
- `POST /api/v1/emails/{id}/verification`: Record user verification check items or candidate override (preserves original risk score in cryptographic audit trail).

### Job Agent & Application Dispatch
- `GET /api/v1/jobs/{email_id}/preview`: Extract structured job specification and compute skill match percentage against candidate profile.
- `POST /api/v1/jobs/{email_id}/draft`: Generate tailored cover letter, recruiter reply email, and interview talking points using Azure AI Foundry Phi-4-mini or local fallback.
- `POST /api/v1/jobs/{email_id}/send`: Explicitly approved application dispatch (handles no-reply detection vs direct SMTP email revert-back; records application package).
- `GET /api/v1/applications`: List all submitted or prepared job application packages for this session.

### Candidate Profile & Private Resume
- `GET /api/v1/profile`: Retrieve candidate profile details.
- `PUT /api/v1/profile`: Update candidate profile details (name, contact, education, skills).
- `DELETE /api/v1/profile`: Clear candidate profile information for this session.
- `POST /api/v1/profile/resume`: Upload resume (PDF, DOCX, TXT; 10MB max; validated magic bytes). Stored in private session storage.
- `GET /api/v1/profile/resume`: Secure download of current candidate resume.
- `DELETE /api/v1/profile/resume`: Permanently delete uploaded resume file from private storage.

### Preferences & Cryptographic Audit Log
- `GET /api/v1/preferences`: Retrieve automation preferences (`auto_quarantine_enabled`, `auto_quarantine_threshold`, `auto_apply_enabled`).
- `PUT /api/v1/preferences`: Update automation preferences.
- `GET /api/v1/audit`: Query tamper-evident security audit log.
- `GET /api/v1/audit/verify`: Verify SHA-256 cryptographic hash chain integrity across all audit records.
