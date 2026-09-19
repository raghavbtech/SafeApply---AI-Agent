# 🛡️ SafeApply — AI Recruitment Scam Detector & Career Safety Platform

> **Account-Free, Privacy-First AI Recruitment Security and Career Navigation Platform for Students & Job Seekers**
>
> *Developed for Azure Student Evaluation*

[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20Tailwind-61DAFB.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20REST%20API-009688.svg)](https://fastapi.tiangolo.com/)
[![Azure AI Foundry](https://img.shields.io/badge/Azure%20AI-Foundry%20(Phi--4--mini--instruct)-0078D4.svg)](https://portal.azure.com/)
[![Azure AI Search](https://img.shields.io/badge/Azure%20AI-Search%20(F0%20Tier)-008AD7.svg)](https://azure.microsoft.com/)
[![Azure AI Language](https://img.shields.io/badge/Azure%20AI-Language%20(F0%20Tier)-00B4D8.svg)](https://azure.microsoft.com/)
[![Responsible AI](https://img.shields.io/badge/Responsible%20AI-Grounded-success.svg)](https://www.microsoft.com/ai/responsible-ai)

---

## 📌 Project Overview & Team

- **Project Title:** SafeApply — AI Recruitment Scam Detector & Career Safety Platform
- **Target Audience:** College and university students navigating campus placements, internships, and entry-level recruitment.
- **Team Members:** Raghav & Team
- **Demonstrated AI & Cloud Concepts:** Generative AI, Retrieval-Augmented Generation (RAG), EMSCAD Machine Learning Classifier, Agent Orchestration, Evidence Grounding, Responsible AI Safeguards, Zero-Account Public Session Security, and Cryptographic Tamper-Evident Audit Trails.

---

## 🛑 Problem Statement

Students and job seekers are systematically targeted by fraudulent recruitment messages that imitate legitimate employers or promise unrealistic remote salaries. Common scam tactics include:

1. **Upfront fees** disguised as refundable registration deposits, training charges, security deposits, courier insurance, or onboarding payments.
2. **Urgency and pressure tactics** that demand immediate action within minutes or hours under threat of disqualification.
3. **Premature requests for sensitive information** such as Aadhaar, PAN, bank-account details, OTPs, or identity credentials.
4. **Suspicious recruiter domains or communication channels**, including public email providers (`@gmail.com`), typosquatted corporate domains, and chat-only interviews (Telegram/WhatsApp).
5. **Unrealistic compensation or vague hiring processes**, such as unusually high compensation without interviews or screening.
6. **Fake-check and equipment-purchase schemes**, where candidates are instructed to deposit a check and purchase equipment from an unauthorized vendor.

SafeApply provides an explainable, multi-layered risk assessment that helps students detect suspicious recruitment patterns while avoiding unsupported accusations.

---

## 🌐 Public, No-Login, No-Signup Architecture

SafeApply operates as a **100% public, account-free web application**. 

There are **no login pages, no signup forms, no passwords, and no demo credential buttons**.

```
Visitor Opens Site ➔ Server issues anonymous HTTP-only cookie ➔ Immediate access to Scanner, Dashboard & Mailbox
                                                                   │
                                                                   ├─ Optional & skippable candidate profile
                                                                   ├─ Per-session isolated mailbox connection
                                                                   └─ One-click "Delete My Data" permanent erasure
```

### Key Security & Privacy Guarantees:
1. **Unpredictable Server-Side Anonymous Sessions**: On first request, the server automatically generates a cryptographically random session (`anon_<uuid>`). The raw token is delivered exclusively through an HTTP-only, SameSite cookie (`safeapply_session`).
2. **Server-Side Token Hashing**: The server stores only the `SHA-256` hash of the session token. Raw tokens are never stored in databases or log files.
3. **Strict Data Partitioning**: Cosmos DB partition keys (`/user_id`) and local JSON storage use `session_id`. Visitor A can never inspect or alter Visitor B's profile, resume, emails, applications, or audit logs.
4. **Optional & Skippable Onboarding**: Visitors can immediately analyze ad-hoc text or imported `.eml` files without entering personal information. The candidate onboarding modal is fully dismissible with a "Skip for now (Scanner Only)" action. Candidate profile and resume details are only required when calculating skill matching or drafting applications in the Job Agent.
5. **Private Azure Blob Resume Storage**: Uploaded resumes (PDF, DOCX, TXT; 10MB limit) are validated using magic file signatures, stored in private Azure Blob Storage (with local filesystem fallback), and isolated per session. Resumes are downloaded via byte streaming; physical paths are never exposed.
6. **Encrypted Mailbox Credentials**: Personal mailbox connections (IMAP/SMTP) encrypt passwords and app tokens at rest using Fernet/authenticated cipher stream before storage in Cosmos DB. A "Disconnect Mailbox" action permanently deletes stored credentials immediately.
7. **Rate Limiting & CSRF Protection**: Sensitive endpoints are protected by in-memory sliding-window rate limiters. Cookie-authenticated mutation requests validate `Origin` and `Referer` headers against allowed origins.
8. **Complete Data Erasure ("Delete My Data")**: At any time, a visitor can click "Delete My Data" in the header or settings. This invokes `DELETE /api/v1/session/data` which permanently purges the candidate profile, blob-stored resume files, stored emails, job applications, encrypted mailbox credentials, and cryptographic audit records.

---

## 🧭 Streamlined Candidate Navigation (6 Primary Destinations)

SafeApply consolidates its full security and application suite into **exactly six understandable primary destinations**:

1. **Dashboard** (`/dashboard`): Real-time threat status, advisory risk distribution, 4 candidate shortcuts (**Scan Job Offer**, **Upload Resume**, **My Mailbox**, **Job Applications**), recent recruitment emails, and candidate session privacy status.
2. **Scan Job Offer** (`/scan`): Unified text paste and `.eml` analysis flow with the 4-pillar detection pipeline, benchmark presets, and contextual next-step advice.
3. **My Mailbox** (`/inbox`): Unified Active Inbox, Quarantined Threats vault tab (with Restore to Inbox and Quarantine audit tracking), and contextual interactive Verification Checklist for ambiguous offers (with Verify & Trust Offer override).
4. **Job Applications** (`/applications`): Combined Opportunities (job extraction & skill overlap), Prepare Application (tailored drafts, cover letters, recruiter replies, and explicit Human-in-the-Loop approval modal), and History (submission tracking).
5. **My Profile** (`/profile`): High-contrast, Poppins-styled candidate details, education, skill badges, target locations, and resume management.
6. **Settings** (`/settings`): Remote mailbox credentials connection/disconnection, autonomous quarantine and auto-apply thresholds, live SMTP dispatch toggle, and "Delete All My Session Data" privacy controls.

---

## 🏛️ 4-Pillar Detection Architecture

SafeApply unifies four complementary analytical layers to assess any recruitment communication:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Raw Recruitment Text / EML                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼───────────────────────────┐
       ▼                            ▼                           ▼
┌──────────────┐             ┌──────────────┐            ┌──────────────┐
│   Pillar 1   │             │   Pillar 2   │            │   Pillar 3   │
│ Deterministic│             │  EMSCAD ML   │            │ Azure Search │
│ Rules Engine │             │  Classifier  │            │ Grounded RAG │
└──────┬───────┘             └──────┬───────┘            └──────┬───────┘
       │                            │                           │
       └────────────────────────────┼───────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│          Deterministic Evidence Synthesis (0-100 Risk Score)           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Pillar 4: Azure AI Foundry (Phi-4-mini) Grounded Explanation Generator │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│          Post-Generation Grounding Guard & Advisory Disclaimer         │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Deterministic Rules & Heuristics Engine**:
   - Checks recruiter domain authenticity against known corporate domains and public webmail services.
   - Detects salary/compensation anomalies (e.g. $180,000/month for an intern).
   - Identifies upfront fee solicitations, urgency triggers, and premature credential requests.
2. **EMSCAD Machine Learning Classifier**:
   - Calibrated statistical model trained on the Aegean Employment Scam Dataset (**17,880 real-world job postings**).
   - **0.9902 ROC-AUC**, **0.9112 PR-AUC**, **89.47% Precision**, and **98.51% overall accuracy** on unseen holdout test data.
   - Extracts empirical fraud signals (e.g. absence of company logo, missing company profile, telecommuting fraud ratios) and token attributions.
3. **Azure AI Search Evidence-Grounded RAG**:
   - Curated knowledge base of **35 recruitment-fraud patterns**: 20 core taxonomy patterns and 15 authentic historical EMSCAD fraud cases.
   - Category-specific retrieval prevents high-scoring categories from drowning out subtle indicators.
   - All retrieved references require direct textual evidence in the offer before being provided to the synthesis engine.
4. **Azure AI Foundry GenAI (Phi-4-mini-instruct)**:
   - Synthesizes the fixed deterministic score and grounded evidence into a student-friendly explanation.
   - Enforces strict Responsible AI constraints: never hallucinates unobserved demands (e.g. UPI PIN or bank passwords when only bank details were requested).

---

## 💼 Autonomous Job Application Agent

When an email or offer is verified as legitimate (Low Risk), the **Job Agent** assists the candidate:
- **Job Spec Extraction**: Parses job role, hiring company, required technical skills, compensation, and recruiter contact.
- **Candidate Skill Matching**: Evaluates candidate skills from their uploaded profile/resume against job requirements, calculating match percentage, matched skills, and gap areas.
- **Application Package Drafting**: Using Azure AI Foundry or local templates, drafts a formal 4-paragraph cover letter, an email reply to the recruiter, and interview talking points.
- **Human-in-the-Loop Approval Dispatch**: SafeApply never dispatches applications autonomously. The candidate must review the draft, check contact info, and explicitly approve dispatch.
- **No-Reply Detection**: Automatically identifies automated sender addresses (e.g. `no-reply@company.com`) and guides the candidate to the official careers portal.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | React 18, Vite, TypeScript | Lucide React, TailwindCSS, Motion, TanStack Query |
| **Backend API** | FastAPI, Pydantic v2, Uvicorn | Async REST API, HTTP-only session cookies, thread-safe session store |
| **GenAI Explanation** | Azure AI Foundry | Phi-4-mini-instruct via OpenAI-compatible Python SDK |
| **RAG Knowledge Base** | Azure AI Search | 35 Curated taxonomy patterns & EMSCAD real-world cases |
| **Entity Extraction** | Azure AI Language + Heuristics | NER and key phrase extraction |
| **ML Classifier** | Scikit-learn, Joblib | TF-IDF + Calibrated Logistic Regression on 17.8k EMSCAD postings |
| **Persistence** | Azure Cosmos DB / Local JSON | Partitioned by `/user_id` (`session_id`) with complete data purge |
| **Mailbox Integration** | Python `imaplib`, `email` | Per-session IMAP sync, spam routing, MIME `.eml` parsing |
| **Security Audit** | SHA-256 Hash Chain | Tamper-evident cryptographic logging for quarantine & overrides |
| **Legacy Interface** | Streamlit | Preserved parallel interface (`app.py`, `ui_mailbox.py`) |

---

## ⚡ Quick Start & Local Execution

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Clone the Repository
```bash
git clone https://github.com/raghavbtech/SafeApply---AI-Agent.git
cd SafeApply---AI-Agent
```

### 3. Setup Python Backend Environment
```powershell
# Install Python dependencies
pip install -r requirements.txt

# Configure environment credentials
Copy-Item .env.example .env
```

Configure `.env` with your Azure credentials (or leave defaults for local fallback mode):
```ini
AZURE_OPENAI_ENDPOINT=https://your-foundry-endpoint/
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=Phi-4-mini-instruct

SEARCH_ENDPOINT=https://your-search-service.search.windows.net
SEARCH_API_KEY=your_admin_key_here
SEARCH_INDEX_NAME=safeapply-scam-patterns

LANGUAGE_ENDPOINT=https://your-language-service.cognitiveservices.azure.com/
LANGUAGE_API_KEY=your_key_here
```

### 4. Setup React Frontend
```powershell
cd frontend
npm install
cd ..
```

---

## 🚀 Running the Project

### Command 1: Start FastAPI Backend
```powershell
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```
- Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`
- Health Readiness: `http://127.0.0.1:8000/health/ready`

### Command 2: Start React Frontend
```powershell
cd frontend
npm run dev
```
- Open `http://localhost:5173` in your browser.
- The Vite dev server automatically proxies `/api` and `/health` requests to `http://127.0.0.1:8000`.

### Command 3: (Optional) Run Original Streamlit App
```powershell
streamlit run app.py
```
- Accessible on `http://localhost:8501`.

---

## 🧪 Automated Testing & Verification

SafeApply includes automated regression suites covering both backend logic and anonymous session behavior:

```powershell
# 1. Anonymous Sessions, Visitor Isolation & API Security (16 tests)
python -m pytest tests/api/test_anonymous_sessions.py tests/api/test_profile_and_security.py tests/api/test_health_and_session.py -v

# 2. Baseline Agent Workflow & Pipeline Regression (13 tests)
python -m pytest test_agent_workflow.py -v

# 3. Benchmark Scoring, Grounding & RAG Coverage (16 tests)
python test_pipeline.py

# 4. Frontend TypeScript Compilation & Bundling
cd frontend
npm run build
```

---

## 🔒 Responsible AI Principles

1. **Evidence Grounding**: Retrieved RAG documents are reference knowledge, not asserted facts. Explanations must be anchored in the submitted offer text.
2. **Hallucination Prevention**: Strict prompt guards and post-generation regex sanitizers ensure payment requests do not become fake PIN/password allegations.
3. **Deterministic Scoring**: The GenAI model does not set the risk score; a deterministic engine calculates the score first, and the model explains the verified evidence.
4. **False-Positive Resistance**: Protective statements such as *"We never charge candidates recruitment fees"* are treated as legitimate protection unless affirmative payment demands are present.
5. **Advisory, Non-Defamatory Verdicts**: The engine evaluates the specific communication, not the brand, providing actionable guidance for students to verify through official corporate portals or university placement cells.

---

## ☁️ Azure Cloud Deployment

### Backend (Azure App Service / Container Apps):
```bash
# Build and deploy Docker container
az acr build --registry <your-registry> --image safeapply-backend:latest .
az containerapp create --name safeapply-api --resource-group <rg> --image <your-registry>.azurecr.io/safeapply-backend:latest --target-port 8000 --ingress external
```

### Frontend (Azure Static Web Apps):
```bash
cd frontend
npm run build
# Deploy dist/ directory via GitHub Actions or Azure SWA CLI
az staticwebapp create --name safeapply-web --resource-group <rg> --source dist/
```

---

## 📂 Project Structure

```text
SafeApply---AI-Agent/
├── backend/
│   ├── adapters/          # Integration adapters (Repository, SecurityEngine, MailProvider)
│   ├── api/v1/            # FastAPI route controllers (session, analysis, emails, jobs, profiles, etc.)
│   ├── schemas/           # Pydantic v2 validation contracts
│   ├── security/          # Anonymous session store, token hashing, principal definitions
│   ├── services/          # Business logic services (Analysis, Profile, Session, JobAgent)
│   ├── config.py          # Environment settings
│   ├── errors.py          # Typed application exceptions and handlers
│   └── main.py            # FastAPI application factory and middleware
├── frontend/
│   ├── src/
│   │   ├── api/           # Typed REST client with session cookie credentials
│   │   ├── auth/          # SessionContext and SessionProvider
│   │   ├── components/    # Reusable UI components (Header, Sidebar, ScoreCard, Modals)
│   │   ├── layouts/       # AppShell with dismissible onboarding modal
│   │   └── pages/         # Landing, Dashboard, ManualScan, Inbox, EmailDetail, JobAgent, etc.
│   ├── package.json
│   └── vite.config.ts
├── models/                # Trained EMSCAD ML model and model card
├── tests/api/             # Comprehensive pytest API & anonymous session test suites
├── agent.py               # 4-pillar risk assessment orchestration engine
├── azure_db.py            # Cosmos DB & local JSON persistence with data purge
├── job_agent.py           # Job spec extraction, matching, and application generator
├── mail_sync.py           # IMAP mailbox synchronization
├── search_indexer.py      # Azure AI Search index builder
└── requirements.txt       # Python dependencies
```

---

## 📚 Acknowledgments & References

- **Dataset**: Aegean Employment Scam Dataset (EMSCAD) — 17,880 verified job postings.
- **Cloud Services**: Microsoft Azure (Azure AI Foundry, Azure AI Search, Azure AI Language, Azure Cosmos DB).
- **Core Libraries**: FastAPI, Pydantic, Scikit-learn, React, Vite, TailwindCSS, Motion, Lucide.
