# SafeApply — React + FastAPI Migration & Architecture Guide

## Architecture Overview

SafeApply has evolved from a single monolithic Streamlit presentation layer into a modern, decoupled client-server architecture built for public, account-free recruitment security:

1. **Frontend**: React 18 + Vite + TypeScript + TailwindCSS + Motion + Lucide React.
   - Dark neon cyberpunk aesthetic with curated cyan/violet/coral tokens.
   - TanStack Query for reactive server state and real-time polling.
   - **Zero Login / Zero Signup**: Direct access to scanner, dashboard, mailbox, quarantine vault, and verification without login walls or demo credential forms.
   - **Privacy First**: Header and settings include a prominent "Delete My Data" modal triggering complete server-side data purging.
2. **Backend**: FastAPI (`/api/v1`) with Pydantic v2 schemas and modular service adapters.
   - **Server-Side Anonymous Sessions**: Issues unpredictable `safeapply_session` HTTP-only cookies on first visit.
   - **Token Hashing**: Stores only SHA-256 hashes of session tokens on the server.
   - **Strict Data Partitioning**: Cosmos DB `/user_id` partition keys and local JSON database use `session_id` to guarantee 100% tenant isolation across public visitors.
   - **Durable Azure Blob Storage**: Resumes are persisted to private Azure Blob Storage (`azure-storage-blob`) with durable local fallback. Downloaded as streaming bytes; absolute paths are never leaked.
   - **Encrypted Mailbox Credentials**: IMAP/SMTP passwords and app tokens are encrypted at rest with Fernet/authenticated cipher stream before storage in Cosmos DB.
   - **Public API Protection**: Sliding-window rate limiting on sensitive routes (analysis, upload, job dispatch, sync) and CSRF protection on state-changing requests.
   - Wraps tested Python ML (EMSCAD), RAG (Azure AI Search), GenAI (Azure AI Foundry Phi-4-mini), heuristic, IMAP, and SMTP logic through clean adapter layers.
   - Safe defaults: destructive actions and auto-sends require explicit opt-in or human confirmation.
3. **Persistence**: Azure Cosmos DB partitioned by `/user_id` with local JSON (`.safeapply_local_db.json`) fallback. Includes complete data purge method `db_purge_user_data(user_id)` and resume blob purge.
4. **Cloud-Native Azure Deployment**: Docker multi-stage build running as non-root user, Azure Static Web Apps frontend configuration (`staticwebapp.config.json`), and comprehensive deployment instructions with $15/month budget controls (`docs/DEPLOYMENT_AZURE.md`).
5. **Legacy Preservation**: The original Streamlit interface (`app.py` and `ui_mailbox.py`) remains 100% functional side-by-side.

---

## Running Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend (FastAPI)
```powershell
# In repository root
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- API Documentation: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health/ready`

### 3. Frontend (React + Vite)
```powershell
cd frontend
npm run dev
```
- Open `http://localhost:5173` in your browser.
- The Vite dev server automatically proxies `/api` and `/health` requests to `http://127.0.0.1:8000`.

### 4. Running the Legacy Streamlit App (Optional)
```powershell
streamlit run app.py
```
- Runs in parallel on `http://localhost:8501`.

### 5. Running Automated Tests
```powershell
# Original regression suites (13 tests)
python -m pytest test_agent_workflow.py -v
python test_pipeline.py

# FastAPI API, Anonymous Sessions, Blob Storage & Security suite (24 tests)
python -m pytest tests/api/ -v

# Frontend build & typecheck
cd frontend
npm run build
```
