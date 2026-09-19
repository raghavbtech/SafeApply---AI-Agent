# SafeApply — React + FastAPI Migration Guide

## Architecture Overview

SafeApply has been migrated from a single monolithic Streamlit presentation layer into a modern, decoupled client-server architecture:

1. **Frontend**: React 18 + Vite + TypeScript + TailwindCSS + Motion + Lucide React.
   - Dark neon aesthetic with curated cyan/violet/coral tokens.
   - TanStack Query for caching and real-time polling.
   - Strict separation of concern: client never calculates risk scores or holds credentials.
2. **Backend**: FastAPI (`/api/v1`) with Pydantic v2 schemas.
   - Enforces authentication and per-user data ownership on every route.
   - Wraps the tested Python ML, RAG, heuristic, IMAP, and SMTP logic through clean adapter layers.
   - Safe defaults: destructive actions and auto-sends require explicit opt-in or human confirmation.
3. **Persistence**: Azure Cosmos DB partitioned by `/user_id` with local JSON (`.safeapply_local_db.json`) fallback.
4. **Legacy Preservation**: The Streamlit interface (`app.py` and `ui_mailbox.py`) remains 100% functional side-by-side during the transition.

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
# Original regression suites
python -m pytest test_agent_workflow.py -vv
python test_pipeline.py

# FastAPI API & Security suite
python -m pytest tests/api/ -vv

# Frontend build & typecheck
cd frontend
npm run typecheck
npm run build
```
