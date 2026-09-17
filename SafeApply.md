# SafeApply — Autonomous Recruitment Security & Job Application Agent

## 1. Project Overview

**SafeApply** is an AI-powered recruitment security and job-application assistant designed to help users identify suspicious recruitment emails, verify job opportunities, and safely proceed with legitimate applications.

The system combines **AI agent orchestration, Retrieval-Augmented Generation (RAG), machine learning, deterministic security rules, Azure AI services, and mailbox integration**.

SafeApply is not designed as a single fake-job classifier. Instead, the machine-learning classifier is one of several tools available to an AI agent. The agent evaluates evidence from multiple sources and selects the appropriate workflow for each recruitment email.

The long-term goal is to provide an end-to-end recruitment assistant that can:

- Read recruitment-related emails with user permission.
- Detect whether a message is related to a job opportunity.
- Analyze the message for recruitment-scam indicators.
- Generate an evidence-grounded risk score.
- Recommend or perform mailbox actions for suspicious messages.
- Extract structured information from legitimate job opportunities.
- Compare legitimate opportunities against the user's profile or resume.
- Prepare a job application.
- Submit or continue an application only after the appropriate user approval.

---

## 2. Problem Statement

Recruitment scams increasingly use email, messaging platforms, fake recruiter identities, unrealistic compensation claims, advance-fee requests, fake company domains, and requests for sensitive personal information.

Users often have to manually determine:

1. Whether a recruitment email is genuine.
2. Whether the recruiter actually represents the claimed organization.
3. Whether the salary and hiring process are plausible.
4. Whether payment or personal-information requests are suspicious.
5. Whether they should continue with the opportunity.
6. Whether a legitimate opportunity matches their profile.

Most existing solutions address only one part of the problem, such as spam filtering or fake-job classification.

SafeApply addresses the complete workflow by combining **mail ingestion, security analysis, AI reasoning, RAG-based evidence retrieval, ML classification, deterministic verification tools, and an assisted application workflow**.

---

## 3. Core Idea

SafeApply follows an agentic architecture in which the AI agent decides which tools and workflows are required for an incoming recruitment email.

```text
                    ┌─────────────────────┐
                    │ User Email Inbox    │
                    │ Outlook / Gmail     │
                    └──────────┬──────────┘
                               │
                        Mail Connector
                               │
                    ┌──────────▼──────────┐
                    │ SafeApply Mail Agent│
                    └──────────┬──────────┘
                               │
                      Recruitment Email?
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                NO                          YES
                 │                           │
              Ignore                  Analyze Offer
                                             │
       ┌─────────────────────────────────────┼────────────────────────────────────┐
       │                    │                │                 │                   │
       ▼                    ▼                ▼                 ▼                   ▼
 Rules Engine         EMSCAD ML        Azure AI Search    Domain Tool        Salary Tool
       │                    │                │                 │                   │
       └─────────────────────────────────────┼────────────────────────────────────┘
                                             │
                                   Evidence Fusion Engine
                                             │
                                        Risk Score
                                             │
                     ┌───────────────────────┼────────────────────────┐
                     │                       │                        │
                    LOW                    MEDIUM                  HIGH/CRITICAL
                     │                       │                        │
                     ▼                       ▼                        ▼
              Job Agent Flow         Verification Flow        Security Flow
                     │                       │                        │
              Extract Job Data      Request/perform extra     Recommend quarantine
                     │               verification             or move to spam
              Resume Matching
                     │
             Prepare Application
                     │
                User Approval
                     │
                  Apply
```

---

## 4. SafeApply AI Agents

### 4.1 Mail Agent

The Mail Agent acts as the entry point of the workflow.

Responsibilities:

- Connect to the user's mailbox with explicit authorization.
- Read selected or newly received recruitment emails.
- Extract sender, subject, body, URLs, and message metadata.
- Determine whether the message appears recruitment-related.
- Pass relevant messages to the Recruitment Security Agent.

For Microsoft Outlook / Microsoft 365, mailbox integration can be implemented using **Microsoft Graph** with delegated, read-only permissions.

---

### 4.2 Recruitment Security Agent

The Recruitment Security Agent determines whether a recruitment message is trustworthy enough to continue.

It orchestrates multiple tools rather than relying on a single model.

Inputs include:

- Original email body.
- Extracted recruiter and company information.
- Email domain.
- Compensation information.
- Requested actions.
- URLs and company website.
- ML fraud probability.
- RAG evidence.
- Rule-engine output.

The security agent produces:

```text
Risk Level: Low / Medium / High / Critical
Risk Score: 0–100
Evidence: Directly observed indicators
Recommendation: Proceed / Verify / Quarantine
```

---

### 4.3 Verification Agent

Medium-risk opportunities are routed to a verification workflow.

The Verification Agent can:

- Compare recruiter email and company domain.
- Compare email domain with a website contained in the message.
- Check whether the organization identity is internally consistent.
- Identify public email accounts used for claimed corporate recruiting.
- Detect suspicious hiring-process characteristics.
- Present unresolved uncertainty to the user.

The agent should avoid making unsupported claims that a company or recruiter is fraudulent.

---

### 4.4 Job Application Agent

Low-risk job opportunities can be passed to the Job Application Agent.

The Job Agent can extract:

- Company name.
- Job title.
- Location.
- Salary or stipend.
- Required skills.
- Experience requirements.
- Application deadline.
- Application URL.
- Recruiter contact.

Future versions can compare these requirements with the user's resume or profile.

Example:

```text
Company: Example Technologies
Role: Backend Developer
Location: Bengaluru
Salary: ₹8–10 LPA

Required Skills:
✓ Python
✓ REST APIs
✓ SQL
△ Azure
△ Docker

Profile Match: 81%
```

The Job Agent can then prepare the user's application and request final approval before any external submission.

---

## 5. Detection Architecture

SafeApply uses a hybrid detection system.

### 5.1 Deterministic Rule Engine

The rule engine identifies directly observable recruitment-risk indicators.

Examples:

- Advance or registration fee.
- Security deposit.
- Payment through UPI.
- Payment screenshot request.
- Very short acceptance deadline.
- No-interview direct selection.
- Aadhaar/PAN/passport request.
- Bank-account information request.
- OTP, PIN, or password request.
- Fake-check/equipment purchase workflow.
- Telegram/WhatsApp-only recruitment.
- Public Gmail/Yahoo account claiming to represent a major company.

The rule engine provides explainable evidence and should remain independent of the GenAI model.

---

### 5.2 EMSCAD Machine-Learning Classifier

SafeApply uses a supervised machine-learning model trained using the **Employment Scam Aegean Dataset (EMSCAD)**.

The classifier provides an additional statistical signal:

```text
Fraud Probability: 61.5%
ML Risk Band: Medium
```

The classifier does **not** independently determine the final SafeApply risk score.

It acts as one tool within the broader agent pipeline.

This is important because EMSCAD primarily contains full job advertisements, while SafeApply may receive:

- Short emails.
- WhatsApp-style messages.
- Placement notices.
- Job descriptions.
- Recruiter outreach.

Therefore, ML probabilities are treated as advisory evidence rather than absolute fraud probabilities.

---

## 6. Retrieval-Augmented Generation (RAG)

SafeApply uses Azure AI Search as a recruitment-fraud knowledge base.

### 6.1 Curated Scam Pattern Index

Current knowledge base:

```text
safeapply-scam-patterns
```

It contains interpretable recruitment-fraud patterns such as:

- Advance-fee scams.
- Urgency pressure.
- Premature sensitive-information requests.
- Fake-check/equipment scams.
- Domain impersonation.
- Unrealistic salary claims.
- Suspicious hiring-process patterns.

RAG retrieval is **evidence-gated**.

A pattern can only be retrieved as evidence for the current offer if the offer itself contains corresponding observed evidence.

This reduces hallucination and confirmation bias.

---

### 6.2 Historical Job Example Index

A future second index can contain legitimate and fraudulent EMSCAD examples:

```text
safeapply-job-examples
```

This allows retrieval of both:

- Similar fraudulent examples.
- Similar legitimate examples.

The goal is to avoid a RAG system that always returns a scam pattern merely because its knowledge base contains only scams.

---

## 7. GenAI Layer

Azure AI Foundry is used primarily for **grounded explanation generation**.

The GenAI model does not independently determine the risk score.

It receives:

- Original job offer.
- Extracted entities.
- Rule-engine findings.
- Domain-check output.
- Salary-check output.
- ML classifier output.
- Retrieved RAG evidence.
- Fixed deterministic assessment.

It then generates a concise human-readable explanation.

Example:

```text
High Risk — 87/100

The message asks the candidate to pay a refundable registration fee
within two hours and requests identity documents before a formal
interview process. The recruiter also uses a public Gmail address
while claiming to represent a corporate employer. These directly
observed indicators are consistent with known recruitment-scam
patterns.
```

Strict grounding rules prevent the model from introducing claims that are not supported by the original offer.

For example:

```text
"Pay using UPI"
```

must not become:

```text
"Provide your UPI PIN"
```

unless the original message explicitly requests the PIN.

---

## 8. Compensation Normalization

SafeApply normalizes abbreviated compensation formats before performing salary analysis.

Examples:

```text
$5k            → $5,000
$120k/year     → $120,000/year
0.1M/year      → $100,000/year
₹25k/month     → ₹25,000/month
8LPA           → ₹800,000/year
₹1.5L/month    → ₹150,000/month
₹1Cr/year      → ₹10,000,000/year
```

It can also reason about short-duration compensation.

Example:

```text
$5k for 2 hours
```

is normalized as:

```text
Total compensation = $5,000
Equivalent rate = $2,500/hour
```

which can then be treated as an unusually high compensation claim requiring verification.

---

## 9. Risk Fusion

SafeApply combines evidence from multiple tools.

```text
Rules
  +
Domain Verification
  +
Salary Analysis
  +
EMSCAD ML
  +
RAG Evidence
        │
        ▼
Evidence Fusion
        │
        ▼
Final Risk Score
```

Suggested interpretation:

| Score | Risk Level | Agent Action |
|---:|---|---|
| 0–29 | Low | Allow legitimate-job workflow |
| 30–64 | Medium | Trigger additional verification |
| 65–84 | High | Warn user and prevent automatic application |
| 85–100 | Critical | Recommend quarantine/spam |

The final thresholds may be calibrated using validation data and real SafeApply benchmark cases.

---

## 10. Mailbox Automation

### Phase 1 — User-Selected Mail Analysis

The user explicitly selects an email and clicks:

```text
Analyze with SafeApply
```

The email is passed through the full SafeApply security pipeline.

---

### Phase 2 — Inbox Recruitment Scanner

SafeApply periodically or manually scans recent emails and identifies likely recruitment messages.

Example dashboard:

| Email | Company | Risk | Action |
|---|---|---:|---|
| Software Engineer Offer | Microsoft | 8/100 | Review / Apply |
| Remote Assistant Opportunity | Unknown | 61/100 | Verify |
| Urgent Selection Letter | Infosys impersonation | 94/100 | Quarantine |

---

### Phase 3 — Controlled Mail Actions

High-risk emails may be recommended for spam/quarantine.

SafeApply should initially require user confirmation:

```text
SafeApply considers this message Critical Risk (94/100).

[Move to Spam]
[Keep Email]
[Review Evidence]
```

Users may later enable optional automation:

```text
Automatically quarantine recruitment messages with risk ≥ 90
```

---

## 11. Assisted Job Application Workflow

For low-risk opportunities:

```text
SafeApply detects legitimate opportunity
        ↓
Extract job details
        ↓
Analyze job requirements
        ↓
Compare with user profile/resume
        ↓
Generate application package
        ↓
User reviews
        ↓
Agent continues application
```

Possible application artifacts include:

- Tailored resume selection.
- Cover letter.
- Recruiter response.
- Skills summary.
- Application-form answers.
- Application tracking record.

External submission should initially remain user-approved.

---

## 12. Responsible AI and Human Control

SafeApply is intended to assist rather than make irreversible decisions without user awareness.

Core safeguards:

### Evidence Grounding

Every high-risk statement should trace back to observed evidence, tool output, or retrieved supporting information.

### No Automatic Accusations

SafeApply should say:

```text
"This message contains recruitment-scam indicators."
```

rather than:

```text
"This company is fraudulent."
```

unless independently established evidence supports such a statement.

### Human Approval for High-Impact Actions

Initial implementation should require confirmation before:

- Moving an email to spam.
- Deleting an email.
- Sharing personal information.
- Sending an application.
- Submitting a form.
- Contacting a recruiter.

### Minimal Mail Permissions

Mailbox connectors should request only the permissions needed for the selected workflow.

Read-only access is preferred for initial implementation.

Write permissions should only be requested when features such as moving messages or sending applications are enabled.

---

## 13. Proposed Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Core Backend | Python |
| GenAI | Azure AI Foundry |
| Current Foundry Model | Phi-4-mini-instruct |
| RAG | Azure AI Search |
| NLP / Entity Extraction | Azure AI Language + Regex |
| ML | Scikit-learn / EMSCAD |
| Mail Integration | Microsoft Graph |
| Identity / OAuth | Microsoft Entra ID |
| Data Processing | Pandas / NumPy |
| Model Persistence | Joblib |
| Testing | Pytest |
| Version Control | Git / GitHub |

Future Gmail support may be implemented using Google's Gmail API or an appropriate connector after the Outlook/Microsoft 365 workflow is stable.

---

## 14. Current SafeApply Pipeline

The current implementation already includes:

- Recruitment-offer text analysis.
- Entity extraction.
- Requested-action normalization.
- Company/domain extraction.
- Salary extraction.
- Compact salary notation handling.
- Azure AI Search RAG.
- Evidence-gated fraud pattern retrieval.
- Domain verification.
- Salary sanity analysis.
- EMSCAD ML classification.
- Deterministic risk fusion.
- Azure AI Foundry explanation.
- Hallucination-grounding safeguards.
- Streamlit frontend.
- Responsible AI disclaimer.
- Automated pytest checks.
- Benchmark and grounding tests.

The next major development stage is **mailbox integration and agent-controlled actions**.

---

## 15. Planned Development Roadmap

### Phase 1 — Recruitment Risk Engine

Status: **Implemented / actively improving**

Components:

- Rules.
- RAG.
- ML.
- Domain analysis.
- Salary analysis.
- GenAI explanation.
- Grounding tests.

---

### Phase 2 — Mail Integration

Planned components:

- Microsoft Entra authentication.
- Microsoft Graph connection.
- Read selected Outlook emails.
- Recruitment-email detection.
- Analyze selected mail directly in SafeApply.

---

### Phase 3 — Mail Security Agent

Planned components:

- Automatic recruitment-email discovery.
- Risk-based inbox dashboard.
- Recommended spam/quarantine actions.
- User-approved mailbox actions.
- Optional high-confidence automation.

---

### Phase 4 — Job Opportunity Agent

Planned components:

- Job requirement extraction.
- Resume/profile ingestion.
- Skill matching.
- Opportunity ranking.
- Application readiness assessment.

---

### Phase 5 — Application Agent

Planned components:

- Cover-letter generation.
- Recruiter email drafting.
- Application-form preparation.
- User approval.
- Supported application submission.
- Application status tracking.

---

## 16. Example End-to-End Workflow

### Legitimate Opportunity

```text
Incoming Mail
      ↓
Recruitment-related
      ↓
Domain verified
ML probability low
No scam RAG evidence
Salary plausible
No suspicious action requests
      ↓
Risk = 10/100
      ↓
Job Agent
      ↓
Extract role and requirements
      ↓
Profile match = 84%
      ↓
Prepare application
      ↓
User approves
      ↓
Submit / continue application
```

### Suspicious Opportunity

```text
Incoming Mail
      ↓
Recruitment-related
      ↓
No interview
$5k for 2 hours
Registration fee
Public Gmail
Aadhaar requested
      ↓
Rules + ML + RAG + Domain + Salary
      ↓
Risk = 96/100
      ↓
Security Agent
      ↓
Explain evidence
      ↓
Recommend quarantine
      ↓
User approves
      ↓
Move to Spam
```

---

## 17. Project Positioning

SafeApply should be positioned as:

> **An autonomous, evidence-grounded recruitment security and job-application agent that uses machine learning, RAG, deterministic verification tools, GenAI, and mailbox integrations to protect users from recruitment scams while helping them act on legitimate opportunities.**

The key technical distinction is:

```text
Machine Learning ≠ SafeApply

Machine Learning = one SafeApply tool

RAG = one SafeApply knowledge source

Rules = one SafeApply evidence source

Azure services = specialized SafeApply tools

AI Agent = orchestrator that selects tools and actions
```

This architecture allows SafeApply to demonstrate genuine **agentic AI behavior** rather than functioning only as a binary fake-job classifier.

---

## 18. Current Objective

The immediate next milestone is to implement the **SafeApply Mail Analyzer** using Microsoft Outlook / Microsoft 365 integration.

The first version should:

1. Authenticate the user.
2. Read user-selected recruitment emails.
3. Convert email content into the existing SafeApply input format.
4. Run the complete SafeApply analysis pipeline.
5. Display the final risk score and supporting evidence.
6. Allow the user to choose whether to keep, review, or move suspicious messages.
7. Route low-risk opportunities to the future Job Application Agent.

This milestone will transform SafeApply from a standalone recruitment-text analyzer into an integrated AI recruitment-security agent.
