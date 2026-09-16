# SafeApply — AI Recruitment Scam Detector
### Detailed Build Guide — Full Instructions & In-Depth Steps

**One-liner:** SafeApply is an AI agent that flags scam red flags in job offers — fake fees, mismatched domains, unrealistic salaries — and gives students a clear risk score with a plain explanation of why.

**AI-103 concepts demonstrated:** GenAI, RAG, Agent orchestration, Tool use, Responsible AI

**Submission requirements (mandatory):**
- Working Prototype / PoC — demonstrated end-to-end
- GitHub repository with source code + README
- 5-minute video, uploaded to YouTube (720p min, 1080p preferred)
- One combined PDF containing: project title + team members, clickable prototype link (or PPT with screenshots), clickable GitHub link, clickable YouTube link
- YouTube link also pasted separately into the LMS free-text submission field

**Priority order if time runs short:**
1. Keep only the RAG-based red-flag checker tool (drop domain/salary tools) — still satisfies agent + tools + RAG
2. Drop screenshot/PDF upload support — pasted text input only is fine
3. Use a bare-bones Streamlit form instead of a polished frontend
4. Never cut: README completeness, a working live demo, and the Responsible AI disclaimer — these are explicitly graded and cheap to deliver well

---

## STEP 1 — Azure Resource Setup

### 1.1 Confirm your credit
- Log into [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students) with your college email
- Go to **Azure Portal → Cost Management + Billing** and confirm the $100 credit shows as active
- Only one team member needs this — but make sure that person is available throughout the build (they'll own the subscription)

### 1.2 Create a Resource Group
- In the Azure Portal search bar, type **"Resource groups"** → click **Create**
- Name it something clear, e.g. `safeapply-rg`
- Pick a region physically close to you (e.g. Central India) — lower latency, sometimes better free-tier availability
- Click **Review + Create**, then **Create**

### 1.3 Create a Microsoft Foundry Project
- Search **"Azure AI Foundry"** in the portal → **Create new project**
- Attach it to `safeapply-rg`
- Inside the project, go to **Model deployments** → deploy a GPT model
  - Recommended: **GPT-4o-mini** — cheaper and faster, sufficient for reasoning/summarization tasks like this
- Once deployed, go to the project's **Overview** or **Keys and Endpoint** section
- Copy and securely save:
  - **Endpoint URL**
  - **API key**
- **Do not** paste these directly into code files — put them in a `.env` file (see Step 1.6)

### 1.4 Create an Azure AI Search Resource
- Search **"Azure AI Search"** → **Create**
- Choose the **Free tier** (F0) if available — sufficient for a small index of 15–30 documents
- Name it, attach to `safeapply-rg`, same region as your Foundry project if possible
- Once created, go to **Settings → Keys** and copy:
  - **Search service endpoint**
  - **Admin API key**

### 1.5 Create an Azure AI Language Resource
- Search **"Language service"** → **Create**
- Choose **Free (F0)** tier
- Attach to `safeapply-rg`
- Copy the **Endpoint** and **Key 1** from the resource's **Keys and Endpoint** page

### 1.6 Secure your credentials
- Create a `.env` file in your project root:
  ```
  FOUNDRY_ENDPOINT=your_endpoint_here
  FOUNDRY_API_KEY=your_key_here
  SEARCH_ENDPOINT=your_endpoint_here
  SEARCH_API_KEY=your_key_here
  LANGUAGE_ENDPOINT=your_endpoint_here
  LANGUAGE_API_KEY=your_key_here
  ```
- Add `.env` to `.gitignore` **before your first commit** — do this immediately, not later
  ```
  echo ".env" >> .gitignore
  ```
- Never hardcode keys directly into any `.py` file — always load via `os.environ` or a library like `python-dotenv`

---

## STEP 2 — Build the Scam-Pattern Dataset

### 2.1 Decide on categories
Cover these recognizable categories (aim for 3–5 examples per category, ~15–20 total):
- **Upfront fee requests** — registration fees, security deposits, "training material" charges
- **Urgency/pressure tactics** — "respond within 2 hours," "limited slots remaining"
- **Domain mismatches** — claims to represent a known company but uses a generic email (gmail/yahoo/outlook)
- **Unrealistic salary-to-role ratio** — entry-level role promising unusually high pay with no clear justification
- **Premature personal info requests** — asking for bank details, Aadhaar, or ID copies before any real interview process
- **Vague role/process** — no clear job description, no interview, "instant hiring"

### 2.2 Write the examples
- For each category, write 3–5 short realistic snippets (you can construct these yourselves — no need to scrape real scam emails)
- Format each as a structured record:
  ```json
  {
    "category": "upfront_fee",
    "pattern": "Asks for registration or security deposit before confirming role",
    "example_text": "Congratulations! To confirm your internship slot, please pay a refundable registration fee of ₹999 within 24 hours."
  }
  ```
- Save all records into a single JSON or CSV file, e.g. `scam_patterns.json`

### 2.3 Document your sourcing
- In your README, note: "Scam pattern examples were constructed by the team based on commonly reported recruitment fraud patterns (referencing publicly documented scam types), not scraped from real correspondence."
- This satisfies the "acknowledge resources" requirement without needing an external dataset license

### 2.4 Index into Azure AI Search
- Use the Azure AI Search SDK (Python: `azure-search-documents`) to:
  1. Create an index schema (fields: `id`, `category`, `pattern`, `example_text`)
  2. Optionally generate embeddings for `example_text` if you want vector search (use a small embedding model via Foundry) — or start simpler with keyword/full-text search if time is tight
  3. Upload your JSON records as documents into the index
- Test with a simple query script: search for a known phrase and confirm it returns the matching record

---

## STEP 3 — Build the Extraction Pipeline

### 3.1 Set up Azure AI Language client
- Install SDK: `pip install azure-ai-textanalytics`
- Initialize client using your `LANGUAGE_ENDPOINT` and `LANGUAGE_API_KEY` from `.env`

### 3.2 Define what to extract
From a pasted job offer, extract:
- **Company name** (named entity recognition)
- **Salary figure** (look for currency/number entities, or use key phrase extraction + regex as a fallback)
- **Contact email/domain** (regex extraction — Azure Language won't reliably catch this, so combine with simple Python regex)
- **Requested actions** (key phrase extraction — look for phrases like "pay," "transfer," "send copy of")

### 3.3 Write the extraction function
- Input: raw pasted text
- Output: a structured dictionary, e.g.:
  ```python
  {
    "company_name": "TechCorp Solutions",
    "salary": "₹8,00,000/year",
    "contact_domain": "gmail.com",
    "requested_actions": ["pay registration fee", "send bank details"]
  }
  ```

### 3.4 Test it
- Run 5–10 sample offers (mix of realistic legitimate and fake ones) through this function
- Manually check: did it correctly identify company name, salary, domain, and any suspicious requested actions?
- Fix obvious extraction failures before moving to Step 4 — this is your foundation, errors here cascade

---

## STEP 4 — Build RAG Retrieval

### 4.1 Write the retrieval function
- Input: the extracted offer text (or a summary of it)
- Query your Azure AI Search index for the most similar known scam patterns
- Output: top 2–3 matching patterns with their category and pattern description

### 4.2 Test retrieval quality
- Try a query containing "please pay ₹999 registration fee" — confirm it retrieves your `upfront_fee` pattern record
- Try an unrelated/neutral query (e.g., a normal job offer with no red flags) — confirm it either returns nothing strongly relevant or low-confidence matches
- Adjust your search query construction (e.g., which fields to search, whether to use exact phrase vs. broader match) if results are poor

---

## STEP 5 — Build Tools and Agent Orchestration

### 5.1 Tool 1 — Red-Flag Pattern Checker (build this first, highest priority)
- Wraps your Step 4 retrieval function
- Input: extracted offer data
- Output: list of matched scam patterns with categories

### 5.2 Tool 2 — Domain/Company Verification
- Simple logic: compare the claimed company name against the sender's email domain
- Example check: does "techcorp.com" appear in or relate to "TechCorp Solutions"? If the domain is generic (gmail, yahoo, outlook) and the offer claims to be from an established company, flag it
- This can be pure Python string logic — no need for a live company database lookup unless you have time to spare

### 5.3 Tool 3 — Salary Sanity Checker
- Define rough salary bands by role type (e.g., "internship": ₹0–25,000/month, "entry-level full-time": ₹3–8 LPA) — hardcode a small lookup table
- Compare the extracted salary against the relevant band
- Flag significant mismatches (e.g., an "entry-level" role offering ₹50 LPA)

### 5.4 Wire tools into a Foundry agent
- Define each tool as a callable function with a clear name and description (this is what lets the agent decide when to call it)
- Set up the agent in Microsoft Foundry so that, given the extracted offer data, it calls all three tools (or as many as you've built) and collects their outputs
- Test the agent's tool-calling behavior — confirm it actually invokes each tool and receives structured responses back

---

## STEP 6 — Build the GenAI Synthesis Layer

### 6.1 Design the final prompt
Your prompt to the GenAI model should include:
- The extracted offer data
- The outputs from all tools (matched scam patterns, domain check result, salary check result)
- Clear instructions:
  - Synthesize findings into a risk verdict: **Low / Medium / High**
  - Explain the verdict in plain English, referencing specific red flags found
  - Explicitly state this is **advisory only**, not a definitive judgment
  - Avoid absolute accusations against named companies — phrase cautiously (e.g., "this pattern is commonly associated with..." rather than "this company is a scam")

### 6.2 Example prompt structure
```
You are a recruitment fraud risk assessor. Given the following extracted job offer
details and analysis results, provide a risk verdict (Low/Medium/High) and a clear,
plain-English explanation citing specific red flags. Be advisory, not definitive.
Do not make absolute accusations against any named company.

Extracted data: {extracted_data}
Matched scam patterns: {rag_results}
Domain check result: {domain_check}
Salary check result: {salary_check}

Respond in this format:
Risk Level: [Low/Medium/High]
Explanation: [plain-English reasoning]
```

### 6.3 Test the full pipeline end-to-end
- Paste a full job offer → extraction → RAG retrieval → tools → GenAI synthesis → verdict
- Confirm the output is coherent, correctly reflects the red flags found, and reads naturally

---

## STEP 7 — Build the Frontend

### 7.1 Choose Streamlit (fastest option)
- Install: `pip install streamlit`
- Build a single-page app:
  ```python
  import streamlit as st

  st.title("SafeApply — Job Offer Risk Checker")
  offer_text = st.text_area("Paste the job offer text here:")
  if st.button("Check Risk"):
      # call your pipeline function here
      result = run_pipeline(offer_text)
      st.write(f"**Risk Level:** {result['risk_level']}")
      st.write(f"**Explanation:** {result['explanation']}")
  ```

### 7.2 Add visual polish (only if time allows)
- Color-code the risk badge (green/yellow/red)
- Show which specific red flags were matched, as a bullet list
- Add the Responsible AI disclaimer text visibly on the page

### 7.3 Run and test locally
- `streamlit run app.py`
- Confirm it correctly displays results for a few test inputs before moving on

---

## STEP 8 — Testing

### 8.1 Test each component individually first
- **Extraction:** 3–4 sample offers, verify fields are pulled correctly
- **RAG:** known scam phrase query, verify correct pattern match returned
- **Tools:** test each tool individually with an obvious trigger case

### 8.2 Build a small test suite (9–12 cases total)
Prepare 3 examples of each:

| Category | Example characteristics | Expected verdict |
|---|---|---|
| Clearly fake | Fee request + urgency + generic domain + vague role | High risk |
| Clearly legitimate | Real company domain, no fees, standard language | Low risk |
| Ambiguous | Informal email but no fee request, unclear signals | Medium risk |

- Run each through the full pipeline
- Record input/output pairs — this becomes your README's "Testing and Results" section

### 8.3 Specifically test for false positives
- Run a genuinely legitimate-sounding offer and confirm the system does **not** wrongly flag it High risk
- This is the single most important test for your Responsible AI section — document this test explicitly

### 8.4 Check graceful failure
- Test with empty input, gibberish text, or a very short offer
- Confirm the app doesn't crash — shows a sensible message instead

### 8.5 Time the pipeline
- Note how long a full query takes end-to-end
- If it's slow (15–20+ seconds), mention this as a known limitation in your README rather than risk it surprising you live

---

## STEP 9 — Documentation (README.md)

Include these sections:
- **Project title and team members**
- **Problem statement** — recruitment scams targeting students, especially during placement season
- **Solution overview** — one paragraph explaining the agent's flow
- **Architecture / data flow diagram** — extraction → RAG → tools → GenAI verdict (use a simple text diagram or draw one)
- **Technology stack** — Microsoft Foundry, Azure AI Search, Azure AI Language, Streamlit, Python
- **Setup instructions** — how to install dependencies, set up `.env`, run locally
- **Testing and results** — your 9–12 test cases with input/output summaries
- **Known limitations** — e.g., can't verify real-time company legitimacy, advisory only, pipeline latency
- **Future improvements** — browser extension, WhatsApp bot integration, larger scam-pattern database
- **Acknowledgments** — note that scam patterns were team-curated based on commonly reported fraud types; list any libraries used (Streamlit, Azure SDKs, etc.)

---

## STEP 10 — Video Recording

Structure (max 5 minutes):

| Section | Time | What to say/show |
|---|---|---|
| Introduction | 30 sec | Team names, project title, one-line use case |
| Problem statement | 30 sec | Why recruitment scams matter right now, to your own class |
| AI-driven solution | 1 min | Explain GenAI + RAG + agent + tools approach briefly |
| Technical demonstration | 2 min | Live: paste a fake offer → show High risk verdict; paste a real offer → show Low risk verdict |
| Impact & future scope | 1 min | Real value to classmates now; future ideas (browser extension, WhatsApp integration) |

- Record at 1080p if possible (720p is the minimum)
- Upload to YouTube, set sharing to "Unlisted" or "Public" (not Private) so it's accessible
- Double-check the link works in an incognito browser window before submitting

---

## STEP 11 — Submission Packaging

### 11.1 Assemble the PDF
Create one PDF containing:
- Project title and team member names
- Clickable link to the prototype (if hosted — e.g. Streamlit Community Cloud deployment) OR a short PPT with screenshots exported into the same PDF if not hosted
- Clickable link to the GitHub repository
- Clickable link to the YouTube video

### 11.2 Verify before submitting
- Open the exported PDF and click every link — PDF exports sometimes break hyperlinks, so always verify after export, not before
- Paste the YouTube link separately into the LMS free-text submission field
- Submit with time to spare — don't wait until the final minutes in case of upload issues

---

## Final Checklist

- [ ] Working prototype demonstrates the problem, AI approach, AI-103 concepts, and a live technical workflow
- [ ] GitHub repo accessible, README complete, code clean and commented
- [ ] `.env` and all credentials excluded from Git
- [ ] 5-minute video finished, on YouTube, link tested in incognito mode
- [ ] Submission PDF created with all links tested after export
- [ ] YouTube link also pasted into the LMS free-text field
- [ ] Team member info correct in LMS registration
- [ ] Third-party resources and dataset sourcing acknowledged in README
- [ ] Tested for false positives on a legitimate job offer example
- [ ] Responsible AI disclaimer visible in the UI
