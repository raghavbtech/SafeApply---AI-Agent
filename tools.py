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
RAG_TOP_K = int(os.getenv("SAFEAPPLY_TOP_K", "5"))

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com",
    "icloud.com", "mail.com", "yandex.com", "rediffmail.com", "aol.com",
    "live.com", "gmx.com"
}


KNOWN_COMPANY_DOMAINS = {
    "microsoft": "microsoft.com",
    "infosys": "infosys.com",
    "razorpay": "razorpay.com",
    "amazon": "amazon.com",
    "google": "google.com",
}


def load_cached_patterns():
    if os.path.exists(DATASET_PATH):
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ==========================================
# TOOL 1: RED-FLAG PATTERN CHECKER (RAG)
# ==========================================
def _collect_observed_evidence(offer_text: str, extracted_data: dict = None) -> dict:
    """
    Identify evidence directly present in the current offer.

    RAG documents are reference patterns only. A retrieved category is allowed
    into the final tool output only when the current offer contains direct
    evidence supporting that category.
    """
    text = offer_text.lower()
    extracted_data = extracted_data or {}
    evidence = {}

    def add(category: str, message: str):
        evidence.setdefault(category, [])
        if message not in evidence[category]:
            evidence[category].append(message)

    fee_terms = (
        r"registration fee|registration charge|"
        r"security deposit|security charge|"
        r"refundable fee|refundable charge|"
        r"processing fee|processing charge|"
        r"onboarding fee|onboarding charge|"
        r"insurance fee|insurance charge|"
        r"clearance fee|clearance charge|"
        r"training fee|training charge"
    )

    fee_patterns = [
        rf"\b(?:pay|deposit|transfer|remit)\b.{{0,120}}\b(?:{fee_terms})\b",
        rf"\b(?:{fee_terms})\b.{{0,120}}\b(?:pay|deposit|transfer|remit|upi)\b",
    ]

    if any(re.search(pattern, text) for pattern in fee_patterns):
        add("upfront_fee", "The offer asks the candidate to make an upfront fee or deposit payment.")

    if re.search(r"\bwithin\s+\d+\s+(?:minutes?|hours?)\b", text):
        add("urgency_pressure", "The offer imposes a short deadline measured in minutes or hours.")

    if any(
        phrase in text
        for phrase in [
            "permanently cancelled",
            "offer will be revoked",
            "candidature will be cancelled",
            "blacklisted",
            "expires today",
            "immediately or",
        ]
    ):
        add("urgency_pressure", "The offer threatens cancellation or another penalty for delayed action.")

    if any(
        phrase in text
        for phrase in ["bank account", "bank details", "account number", "ifsc"]
    ):
        add("premature_personal_info", "The offer requests bank-account information.")

    if any(
        phrase in text
        for phrase in ["aadhaar", "aadhar", "pan card", "passport copy"]
    ):
        add("premature_personal_info", "The offer requests government identity documents.")

    if any(
        phrase in text
        for phrase in ["upi pin", "net banking password", "internet banking password", " otp", "otp "]
    ):
        add("premature_personal_info", "The offer requests authentication credentials or secrets.")

    if any(
        phrase in text
        for phrase in [
            "no interview required",
            "no interview needed",
            "direct selection",
            "instant hiring",
            "instant offer",
        ]
    ):
        add("vague_role_process", "The candidate is offered or selected without a normal interview process.")

    domain = str(extracted_data.get("contact_domain", "")).lower()
    if domain in GENERIC_DOMAINS:
        add("domain_mismatch", f"The recruiter uses a public email provider (@{domain}).")

    if "telegram" in text:
        add("domain_mismatch", "The offer directs the candidate to Telegram for recruitment communication.")

    if any(
        phrase in text
        for phrase in ["75,000 per month", "36 lpa", "36,00,000", "5,000 per day", "15,000 per day"]
    ):
        add(
            "salary_ratio",
            "The offer contains compensation commonly associated with unrealistic entry-level or task-work claims.",
        )

    if "check" in text and any(
        phrase in text
        for phrase in ["purchase equipment", "purchase software", "buy equipment", "workstation", "office software"]
    ):
        add(
            "fake_check_equipment",
            "The offer mentions sending a check to fund equipment or software purchases.",
        )

    return evidence


def check_red_flags_rag(offer_text: str, extracted_data: dict = None) -> list:
    """
    TOOL 1 (Highest Priority): Red-Flag Pattern Checker.

    Retrieves fraud-pattern references from Azure AI Search (or the local
    curated dataset) while grounding every returned category in evidence
    directly observed in the current offer.
    """
    extracted_data = extracted_data or {}
    observed = _collect_observed_evidence(offer_text, extracted_data)

    if not observed:
        return []

    query_parts = []

    for action in extracted_data.get("requested_actions", []):
        if action:
            query_parts.append(str(action))

    for category, evidence_items in observed.items():
        query_parts.append(category.replace("_", " "))
        query_parts.extend(evidence_items)

    query_string = " ".join(dict.fromkeys(query_parts))
    query_string = re.sub(r"[^\w\s]", " ", query_string)
    query_string = " ".join(query_string.split())[:900]

    if SEARCH_ENDPOINT and SEARCH_API_KEY and "your-search-service" not in SEARCH_ENDPOINT:
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient

            client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(SEARCH_API_KEY),
                connection_timeout=5,
                read_timeout=8,
            )

            best_by_category = {}

            # Query each directly observed category independently. This avoids
            # one high-scoring category crowding another category out of the
            # global Azure Search result set.
            for category, evidence_items in observed.items():
                category_query_parts = [
                    category.replace("_", " "),
                    *evidence_items,
                    *[
                        str(action)
                        for action in extracted_data.get("requested_actions", [])
                    ],
                ]

                category_query = " ".join(category_query_parts)
                category_query = re.sub(r"[^\w\s]", " ", category_query)
                category_query = " ".join(category_query.split())[:700]

                escaped_category = category.replace("'", "''")

                results = client.search(
                    search_text=category_query if category_query else "*",
                    search_fields=["pattern", "example_text", "category"],
                    filter=f"category eq '{escaped_category}'",
                    select=["id", "category", "pattern", "example_text", "risk_weight"],
                    top=1,
                )

                for result in results:
                    score = float(result.get("@search.score", 0.0))

                    best_by_category[category] = {
                        "id": result["id"],
                        "category": category,
                        "pattern": result["pattern"],
                        "score": round(score, 2),
                        "risk_weight": result.get("risk_weight", "medium"),
                        "evidence": evidence_items,
                    }
                    break

            matches = sorted(
                best_by_category.values(),
                key=lambda item: item["score"],
                reverse=True,
            )

            if matches:
                return matches[:RAG_TOP_K]

        except Exception as e:
            print(
                f"[RAG Warning] Azure AI Search query error: {e}. "
                "Falling back to local pattern matcher."
            )

    patterns = load_cached_patterns()
    best_by_category = {}

    query_words = {
        word for word in query_string.lower().split()
        if len(word) > 3
    }

    for pattern in patterns:
        category = pattern["category"]

        if category not in observed:
            continue

        source = (
            f"{pattern['category']} "
            f"{pattern['pattern']} "
            f"{pattern['example_text']}"
        ).lower()

        overlap = sum(1 for word in query_words if word in source)

        item = {
            "id": pattern["id"],
            "category": category,
            "pattern": pattern["pattern"],
            "score": float(overlap),
            "risk_weight": pattern.get("risk_weight", "medium"),
            "evidence": observed[category],
        }

        existing = best_by_category.get(category)
        if not existing or item["score"] > existing["score"]:
            best_by_category[category] = item

    matches = sorted(
        best_by_category.values(),
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches[:RAG_TOP_K]


# ==========================================
# TOOL 2: DOMAIN / COMPANY VERIFICATION
# ==========================================
def verify_company_domain(company_name: str, contact_domain: str, full_email: str = "") -> dict:
    """
    TOOL 2: Domain/Company Verification.

    Flags free/public email providers and suspicious domains. A domain is only
    labelled VERIFIED_DOMAIN when it matches a known organization/domain pair.
    Unknown professional domains remain unverified rather than being treated as
    automatically trusted.
    """
    company_clean = company_name.strip().lower() if company_name else "not specified"
    domain_clean = contact_domain.strip().lower() if contact_domain else "unknown"

    if domain_clean in ["unknown", "not specified"]:
        return {
            "status": "UNVERIFIED",
            "is_flagged": True,
            "severity": "MEDIUM",
            "message": "No official recruiter contact email or domain could be identified.",
        }

    if (
        "telegram" in domain_clean
        or "chat-handle" in domain_clean
        or ("@" in full_email and "." not in contact_domain)
    ):
        return {
            "status": "SUSPICIOUS_CHANNEL",
            "is_flagged": True,
            "severity": "HIGH",
            "message": "Recruiter conducts official communication solely via Telegram/WhatsApp handle without corporate email.",
        }

    if domain_clean in GENERIC_DOMAINS:
        if company_clean not in ["not specified", "freelance", "individual"]:
            return {
                "status": "MISMATCH_GENERIC_DOMAIN",
                "is_flagged": True,
                "severity": "HIGH",
                "message": (
                    f"Sender uses a free public email service (@{domain_clean}) "
                    f"while claiming to represent '{company_name}'. Verify the "
                    "recruiter through the organization's official careers site "
                    "or another independently obtained contact channel."
                ),
            }

        return {
            "status": "GENERIC_DOMAIN",
            "is_flagged": True,
            "severity": "MEDIUM",
            "message": f"Recruiter is using a free public email provider (@{domain_clean}).",
        }

    suspicious_patterns = [r"-hiring", r"-jobs", r"-careers", r"-portal", r"official-"]
    for pattern in suspicious_patterns:
        if re.search(pattern, domain_clean):
            return {
                "status": "POTENTIAL_SPOOFED_DOMAIN",
                "is_flagged": True,
                "severity": "HIGH",
                "message": (
                    f"Domain '@{domain_clean}' contains a naming pattern commonly "
                    "used by unofficial recruitment domains and should be independently verified."
                ),
            }

    for company_token, expected_domain in KNOWN_COMPANY_DOMAINS.items():
        if company_token in company_clean:
            if (
                domain_clean == expected_domain
                or domain_clean.endswith("." + expected_domain)
            ):
                return {
                    "status": "VERIFIED_DOMAIN",
                    "is_flagged": False,
                    "severity": "LOW",
                    "message": (
                        f"Recruiter domain '@{domain_clean}' matches the expected "
                        f"corporate domain for {company_name}."
                    ),
                }

            return {
                "status": "DOMAIN_MISMATCH",
                "is_flagged": True,
                "severity": "HIGH",
                "message": (
                    f"The claimed organization '{company_name}' does not match "
                    f"the expected recruiter domain ('{expected_domain}'); "
                    f"the supplied domain is '@{domain_clean}'."
                ),
            }

    company_tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", company_clean)
        if len(token) >= 4
    ]

    domain_name = domain_clean.split(".")[0]

    if any(token in domain_name for token in company_tokens):
        return {
            "status": "PLAUSIBLE_COMPANY_DOMAIN",
            "is_flagged": False,
            "severity": "LOW",
            "message": (
                f"Domain '@{domain_clean}' is textually consistent with the "
                f"claimed organization, but SafeApply has not independently "
                "verified ownership of the domain."
            ),
        }

    return {
        "status": "PROFESSIONAL_DOMAIN_UNVERIFIED",
        "is_flagged": False,
        "severity": "LOW",
        "message": (
            f"Domain '@{domain_clean}' is not a free email provider, but "
            "SafeApply has not independently verified that it belongs to "
            f"'{company_name}'."
        ),
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


# ==========================================
# TOOL 4: EMSCAD ML FRAUD DETECTOR
# ==========================================
def detect_fraud_ml(offer_text: str, extracted_data: dict = None) -> dict:
    """
    TOOL 4: EMSCAD Machine Learning Fraud Classifier.
    Evaluates empirical scam risk probability using the statistical model
    trained on 17,880 real job postings (addressing the 4.84% class imbalance).
    """
    from ml_classifier import predict_job_offer
    extracted_data = extracted_data or {}
    return predict_job_offer(offer_text, metadata=extracted_data)


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

    print("\nTesting Tool 4 (ML Classifier):")
    res4 = detect_fraud_ml("Urgent data entry work from home earn cash daily via link")
    print(" ", res4)
