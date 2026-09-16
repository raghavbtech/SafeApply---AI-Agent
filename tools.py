"""
SafeApply - Agent Tools
Implements the 3 core AI Agent Tools specified in Step 5:
1. Tool 1: Red-Flag Pattern Checker (RAG retrieval via Azure AI Search / curated dataset)
2. Tool 2: Domain/Company Verification Tool
3. Tool 3: Salary Sanity Checker Tool
"""

import os
import re
import json
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = os.path.join(os.path.dirname(__file__), "scam_patterns.json")
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT", "")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME", "safeapply-scam-patterns")

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com",
    "icloud.com", "mail.com", "yandex.com", "rediffmail.com", "aol.com",
    "live.com", "gmx.com"
}


def load_cached_patterns():
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ==========================================
# TOOL 1: RED-FLAG PATTERN CHECKER (RAG)
# ==========================================
def check_red_flags_rag(offer_text: str, extracted_data: dict = None) -> list:
    """
    TOOL 1 (Highest Priority): Red-Flag Pattern Checker.
    Queries Azure AI Search (or local pattern dataset) using RAG retrieval to find
    matching known recruitment fraud patterns.
    """
    offer_lower = offer_text.lower()
    negation_signals = [
        "no fee", "never charges", "never ask", "never request", "without any fee",
        "no security deposit", "there is no fee", "no charges", "free of charge",
        "does not charge", "will not ask", "zero fee"
    ]
    has_anti_fraud_notice = any(neg in offer_lower for neg in negation_signals)

    # Build a clean targeted search query from actions and text
    search_terms = []
    if extracted_data and extracted_data.get("requested_actions"):
        for act in extracted_data["requested_actions"]:
            kw = act.split("(")[0].strip().strip("'\"")
            if len(kw) > 2:
                search_terms.append(kw)

    raw_query = " ".join(search_terms) if search_terms else offer_text[:120]
    # Remove special punctuation that confuses search syntax
    clean_query = re.sub(r'[^\w\s]', ' ', raw_query)
    query_string = " ".join(clean_query.split()[:12])

    # Attempt live Azure AI Search if credentials exist
    if SEARCH_ENDPOINT and SEARCH_API_KEY and "your-search-service" not in SEARCH_ENDPOINT:
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            credential = AzureKeyCredential(SEARCH_API_KEY)
            client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX_NAME,
                credential=credential,
                connection_timeout=3,
                read_timeout=4,
            )
            results = client.search(
                search_text=query_string if query_string else "*",
                select=["id", "category", "pattern", "example_text", "risk_weight"],
                top=3,
            )
            matches = []
            for r in results:
                score = r.get("@search.score", 0.0)
                if score > 0.5:
                    if r["category"] == "upfront_fee" and has_anti_fraud_notice:
                        continue
                    matches.append({
                        "category": r["category"],
                        "pattern": r["pattern"],
                        "score": round(float(score), 2),
                        "risk_weight": r.get("risk_weight", "high"),
                    })
            if matches:
                return matches
        except Exception as e:
            print(f"[RAG Warning] Azure AI Search query error: {e}. Falling back to pattern matcher.")

    # Local fallback RAG retrieval
    patterns = load_cached_patterns()
    matches = []

    # Specific fraud trigger phrases (actionable demands)
    actionable_triggers = {
        "upfront_fee": [
            "pay a refundable", "pay registration", "registration fee", "pay rs", "pay inr",
            "security deposit", "courier insurance", "transit insurance", "insurance charge",
            "clearance charge", "training material", "purchase the mandatory", "handbook and software kit",
            "registration charge", "pay via upi", "transfer refundable", "refundable transit"
        ],
        "urgency_pressure": [
            "within 2 hours", "within 60 minutes", "within 24 hours", "permanently cancelled",
            "blacklisted from future", "expires strictly at", "urgent notice: only",
            "confirm your attendance by", "by 6:00 pm today", "by 4:00 pm today"
        ],
        "domain_mismatch": [
            "telegram @", "@amazonjobs", "@google-hiring", "careers@google-hiring", "hr.microsoftrecruitment"
        ],
        "salary_ratio": [
            "75,000 per month", "36 lpa", "36,00,000", "5,000 to rs 15,000 per day",
            "subscribing to youtube channels", "daily bonus. no experience"
        ],
        "premature_personal_info": [
            "aadhaar card", "aadhaar", "debit card", "credit card", "pan card",
            "debit card photos", "front photo of debit card", "net banking password",
            "bank account number", "ifsc code", "original 10th, 12th", "physical retention",
            "courier their original", "front and back aadhaar"
        ],
        "vague_role_process": [
            "no interview needed", "direct selection notice", "5-minute chat on whatsapp",
            "duties will be assigned after joining", "no interview, no experience"
        ]
    }

    scored_patterns = []
    for p in patterns:
        category = p["category"]

        # Skip fee checks if legitimate anti-fraud disclaimer is present
        if category == "upfront_fee" and has_anti_fraud_notice:
            continue

        cat_triggers = actionable_triggers.get(category, [])
        # Check if ANY actionable trigger for this category is present
        matched_triggers = [trig for trig in cat_triggers if trig in offer_lower]
        if not matched_triggers:
            continue

        score = len(matched_triggers) * 3

        # Match example text similarity if prominent phrases overlap
        for example_phrase in [p["example_text"][:40].lower(), p["pattern"].lower()]:
            stop_words = {
                "candidate", "selection", "interview", "interviews", "software", "position",
                "company", "campus", "recruitment", "technical", "formal", "process",
                "hiring", "package", "joining", "location", "development", "training",
                "application", "candidates", "letter", "centre", "regarding", "portal",
                "within", "please", "email", "their", "before", "after", "hours"
            }
            key_terms = [w for w in example_phrase.split() if len(w) > 4 and w not in stop_words]
            match_count = sum(1 for term in key_terms if term in offer_lower)
            if match_count >= 2:
                score += 2

        scored_patterns.append((score, p))

    scored_patterns.sort(key=lambda x: x[0], reverse=True)
    for score, p in scored_patterns[:3]:
        matches.append({
            "category": p["category"],
            "pattern": p["pattern"],
            "score": round(min(score / 5.0, 1.0), 2),
            "risk_weight": p.get("risk_weight", "high"),
        })

    return matches


# ==========================================
# TOOL 2: DOMAIN / COMPANY VERIFICATION
# ==========================================
def verify_company_domain(company_name: str, contact_domain: str, full_email: str = "") -> dict:
    """
    TOOL 2: Domain/Company Verification.
    Compares the claimed company name against the sender's email domain or communication channel.
    Flags generic domains (gmail, yahoo) for corporate roles and detects typosquatted/spoofed domains.
    """
    company_clean = company_name.strip().lower() if company_name else "not specified"
    domain_clean = contact_domain.strip().lower() if contact_domain else "unknown"

    # Flag 1: No domain or chat handle only
    if domain_clean in ["unknown", "not specified"]:
        return {
            "status": "UNVERIFIED",
            "is_flagged": True,
            "severity": "MEDIUM",
            "message": "No official recruiter contact email or domain could be identified."
        }

    if "telegram" in domain_clean or "chat-handle" in domain_clean or "@" in full_email and not "." in contact_domain:
        return {
            "status": "SUSPICIOUS_CHANNEL",
            "is_flagged": True,
            "severity": "HIGH",
            "message": "Recruiter conducts official communication solely via Telegram/WhatsApp handle without corporate email."
        }

    # Flag 2: Generic email provider used by corporate entity
    if domain_clean in GENERIC_DOMAINS:
        if company_clean not in ["not specified", "freelance", "individual"]:
            return {
                "status": "MISMATCH_GENERIC_DOMAIN",
                "is_flagged": True,
                "severity": "HIGH",
                "message": f"Sender uses a free public email service (@{domain_clean}) while claiming to represent '{company_name}'. Reputable enterprises recruit exclusively via verified corporate domains."
            }
        else:
            return {
                "status": "GENERIC_DOMAIN",
                "is_flagged": True,
                "severity": "MEDIUM",
                "message": f"Recruiter is using a free public email provider (@{domain_clean})."
            }

    # Flag 3: Typosquatting / deceptive domain
    suspicious_patterns = [r"-hiring", r"-jobs", r"-careers", r"-portal", r"official-"]
    for sp in suspicious_patterns:
        if re.search(sp, domain_clean):
            return {
                "status": "POTENTIAL_SPOOFED_DOMAIN",
                "is_flagged": True,
                "severity": "HIGH",
                "message": f"Domain '@{domain_clean}' appears suspicious and may be mimicking a legitimate organization."
            }

    # Verified domain looks standard
    return {
        "status": "VERIFIED_DOMAIN",
        "is_flagged": False,
        "severity": "LOW",
        "message": f"Domain '@{domain_clean}' appears consistent with professional corporate communication."
    }


# ==========================================
# TOOL 3: SALARY SANITY CHECKER
# ==========================================
def check_salary_sanity(salary_str: str, role_hint: str = "entry-level", offer_text: str = "") -> dict:
    """
    TOOL 3: Salary Sanity Checker.
    Compares extracted compensation against realistic market bands for internships and entry-level jobs.
    Flags absurdly inflated compensation used as recruitment bait.
    """
    if not salary_str or salary_str.lower() in ["not specified", "none", "unknown"]:
        return {
            "is_flagged": False,
            "severity": "LOW",
            "message": "Salary not specified in offer text (standard for initial screening offers)."
        }

    combined_text = f"{salary_str} {offer_text}".lower()

    # Extract numerical value in LPA or monthly
    # Case A: LPA checks (e.g. 36 LPA, 50 LPA)
    lpa_match = re.search(r'(\d+(?:\.\d+)?)\s?(?:lpa|lakhs)', combined_text)
    if lpa_match:
        val = float(lpa_match.group(1))
        if val >= 25.0:
            return {
                "is_flagged": True,
                "severity": "HIGH",
                "claimed_salary": f"{val} LPA",
                "benchmark": "Entry-level market benchmark: ₹3 LPA - ₹10 LPA",
                "message": f"Unusually high compensation ({val} LPA) for entry-level/fresher position without multi-stage technical screening."
            }

    # Case B: Monthly checks for simple/part-time tasks
    # e.g., 75,000 per month for data entry
    monthly_match = re.search(r'(?:inr|rs\.?|₹)?\s?([\d,]+)\s?(?:per month|/month|p\.m\.)', combined_text)
    if monthly_match:
        raw_num = monthly_match.group(1).replace(",", "")
        try:
            num = int(raw_num)
            is_simple_task = any(t in combined_text for t in ["data entry", "form filling", "copy paste", "2 hours", "part time", "no experience"])
            if is_simple_task and num >= 40000:
                return {
                    "is_flagged": True,
                    "severity": "HIGH",
                    "claimed_salary": f"₹{num:,}/month",
                    "benchmark": "Part-time/Data-entry benchmark: ₹5,000 - ₹18,000/month",
                    "message": f"Suspiciously high payout (₹{num:,}/month) for basic part-time/data-entry role requiring no experience."
                }
        except ValueError:
            pass

    # Case C: Daily payouts (e.g., Rs 5,000 to 15,000 per day for YouTube tasks)
    daily_match = re.search(r'(?:inr|rs\.?|₹)?\s?([\d,]+)\s?(?:per day|/day|daily)', combined_text)
    if daily_match:
        return {
            "is_flagged": True,
            "severity": "HIGH",
            "claimed_salary": daily_match.group(0),
            "benchmark": "Standard corporate daily compensation",
            "message": "Daily cash/wallet payout schemes are characteristic of task-based advance-fee fraud."
        }

    return {
        "is_flagged": False,
        "severity": "LOW",
        "claimed_salary": salary_str,
        "message": f"Compensation figure '{salary_str}' is within plausible entry-level parameters."
    }


if __name__ == "__main__":
    print("Testing Tool 1 (RAG):")
    res1 = check_red_flags_rag("Please deposit Rs 1,499 registration fee before appointment")
    print(" ", res1)

    print("\nTesting Tool 2 (Domain):")
    res2 = verify_company_domain("Microsoft India", "gmail.com")
    print(" ", res2)

    print("\nTesting Tool 3 (Salary):")
    res3 = check_salary_sanity("36 LPA", "entry-level", "direct campus selection no interview")
    print(" ", res3)
