# SafeApply — API Contract Specification

All API endpoints are mounted under `/api/v1` (with system health endpoints under `/health`).
Timestamps are UTC ISO-8601 strings. Identifiers are opaque strings. Authentication is via `Authorization: Bearer <token>` or HTTP-only session cookies.

## Endpoints Summary

### System Health
- `GET /health/live`: Basic liveness check.
- `GET /health/ready`: Readiness check testing connectivity to storage (Cosmos/Local DB), Azure AI models, and email config.

### Authentication & Principal
- `POST /api/v1/auth/login`: Authenticate candidate (`username`, `password`), returns token + profile.
- `POST /api/v1/auth/register`: Register new candidate profile.
- `GET /api/v1/auth/me`: Retrieve current authenticated principal.
- `POST /api/v1/auth/logout`: Revoke session.

### Dashboard & Analytics
- `GET /api/v1/dashboard`: Summary statistics (inbox, spam, unscanned, critical, high, medium, low, applied), recent alerts, system status.

### Emails & Ingestion
- `GET /api/v1/emails`: List stored recruitment emails with filtering (`folder`, `status`, `risk_level`, `search`) and cursor/limit pagination.
- `GET /api/v1/emails/{id}`: Detailed email view with full body, sender info, metadata, and latest analysis.
- `POST /api/v1/emails/import-eml`: Upload MIME `.eml` file; parses headers/body, determines recruitment status, stores email.

### Threat Analysis
- `POST /api/v1/analysis/text`: Direct ad-hoc 4-pillar analysis on arbitrary text (presets or custom text).
- `POST /api/v1/emails/{id}/analyze`: Trigger 4-pillar analysis on a stored email.
- `GET /api/v1/emails/{id}/analysis`: Fetch existing 4-pillar analysis results (Rules, ML, RAG, Domain/Salary).

### Mailbox Actions & Security Routing
- `GET /api/v1/mailboxes`: Get connected mailbox status and provider details (credentials never exposed).
- `POST /api/v1/mailboxes/sync`: Trigger asynchronous IMAP mailbox sync and inbox ingestion.
- `POST /api/v1/emails/{id}/spam`: Move email to spam/junk folder (with explicit provider move outcome and local quarantine record).
- `POST /api/v1/emails/{id}/restore`: Restore email from junk folder back to inbox.
- `POST /api/v1/emails/batch-scan`: Run scan across all unscanned emails.

### Verification (Medium-Risk Offers)
- `GET /api/v1/emails/{id}/verification`: Retrieve verification checklist tailored to the ambiguous indicators.
- `POST /api/v1/emails/{id}/verification`: Record user verification check results or candidate override (preserves original risk score in audit).

### Job Agent & Application Dispatch
- `GET /api/v1/jobs/{email_id}/preview`: Extract structured job spec and compute skill match percentage against candidate profile.
- `POST /api/v1/jobs/{email_id}/draft`: Generate tailored cover letter, recruiter reply email, and talking points.
- `POST /api/v1/jobs/{email_id}/send`: Explicitly approved application dispatch (handles no-reply vs direct SMTP email revert-back; records application package).
- `GET /api/v1/applications`: List all submitted or prepared job application packages.

### Candidate Profile & Private Resume
- `GET /api/v1/profile`: Retrieve candidate profile details.
- `PUT /api/v1/profile`: Update candidate profile details.
- `POST /api/v1/profile/resume`: Upload resume (PDF, DOCX, TXT); stored privately.
- `GET /api/v1/profile/resume`: Secure download of current candidate resume.

### Preferences & Audit
- `GET /api/v1/preferences`: Get automation preferences (`auto_quarantine_enabled`, `auto_quarantine_threshold`, `auto_apply_enabled`).
- `PUT /api/v1/preferences`: Update automation preferences.
- `GET /api/v1/audit`: Query tamper-evident security audit log.
- `GET /api/v1/audit/verify`: Verify SHA-256 cryptographic hash chain integrity across all audit records.
