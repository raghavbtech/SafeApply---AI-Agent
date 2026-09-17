"""
SafeApply - Agent Tools

Implements:
1. Evidence-grounded RAG fraud-pattern retrieval
2. Company/domain verification
3. Salary sanity analysis
4. EMSCAD machine-learning fraud classification
"""

import os
import re
import json

from dotenv import load_dotenv

load_dotenv()


# =========================================================
# CONFIGURATION
# =========================================================

DATASET_PATH = os.path.join(
    os.path.dirname(__file__),
    "scam_patterns.json",
)

SEARCH_ENDPOINT = os.getenv(
    "SEARCH_ENDPOINT",
    "",
)

SEARCH_API_KEY = os.getenv(
    "SEARCH_API_KEY",
    "",
)

SEARCH_INDEX_NAME = os.getenv(
    "SEARCH_INDEX_NAME",
    "safeapply-scam-patterns",
)

RAG_TOP_K = int(
    os.getenv(
        "SAFEAPPLY_TOP_K",
        "5",
    )
)


GENERIC_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "protonmail.com",
    "icloud.com",
    "mail.com",
    "yandex.com",
    "rediffmail.com",
    "aol.com",
    "live.com",
    "gmx.com",
}


KNOWN_COMPANY_DOMAINS = {
    "microsoft": "microsoft.com",
    "infosys": "infosys.com",
    "razorpay": "razorpay.com",
    "amazon": "amazon.com",
    "google": "google.com",
}


# =========================================================
# LOCAL RAG DATA
# =========================================================

def load_cached_patterns():

    if os.path.exists(
        DATASET_PATH
    ):

        with open(
            DATASET_PATH,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(
                file
            )

    return []


# =========================================================
# TOOL 1 — OBSERVED EVIDENCE
# =========================================================

def _collect_observed_evidence(
    offer_text: str,
    extracted_data: dict = None,
) -> dict:
    """
    Identify evidence directly appearing in the submitted offer.

    RAG is only allowed to retrieve categories that already have
    observable evidence in the current message.
    """

    text = offer_text.lower()

    extracted_data = (
        extracted_data
        or {}
    )

    evidence = {}

    def add(
        category: str,
        message: str,
    ):

        evidence.setdefault(
            category,
            [],
        )

        if (
            message
            not in evidence[category]
        ):

            evidence[
                category
            ].append(
                message
            )

    # -----------------------------------------------------
    # UPFRONT FEES
    # -----------------------------------------------------

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
        (
            rf"\b(?:pay|deposit|transfer|remit)\b"
            rf".{{0,120}}\b(?:{fee_terms})\b"
        ),

        (
            rf"\b(?:{fee_terms})\b"
            rf".{{0,120}}\b"
            rf"(?:pay|deposit|transfer|remit|upi)\b"
        ),
    ]

    if any(
        re.search(
            pattern,
            text,
        )
        for pattern
        in fee_patterns
    ):

        add(
            "upfront_fee",
            (
                "The offer asks the candidate to make "
                "an upfront fee or deposit payment."
            ),
        )

    # -----------------------------------------------------
    # URGENCY
    # -----------------------------------------------------

    if re.search(
        r"\bwithin\s+\d+\s+(?:minutes?|hours?)\b",
        text,
    ):

        add(
            "urgency_pressure",
            (
                "The offer imposes a short deadline "
                "measured in minutes or hours."
            ),
        )

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

        add(
            "urgency_pressure",
            (
                "The offer threatens cancellation or "
                "another penalty for delayed action."
            ),
        )

    # -----------------------------------------------------
    # PERSONAL / FINANCIAL INFORMATION
    # -----------------------------------------------------

    if any(
        phrase in text
        for phrase in [
            "bank account",
            "bank details",
            "account number",
            "ifsc",
        ]
    ):

        add(
            "premature_personal_info",
            (
                "The offer requests bank-account "
                "information."
            ),
        )

    if any(
        phrase in text
        for phrase in [
            "aadhaar",
            "aadhar",
            "pan card",
            "passport copy",
        ]
    ):

        add(
            "premature_personal_info",
            (
                "The offer requests government "
                "identity documents."
            ),
        )

    if any(
        phrase in text
        for phrase in [
            "upi pin",
            "net banking password",
            "internet banking password",
            " otp",
            "otp ",
        ]
    ):

        add(
            "premature_personal_info",
            (
                "The offer requests authentication "
                "credentials or secrets."
            ),
        )

    # -----------------------------------------------------
    # HIRING PROCESS
    # -----------------------------------------------------

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

        add(
            "vague_role_process",
            (
                "The candidate is offered or selected "
                "without a normal interview process."
            ),
        )

    # -----------------------------------------------------
    # DOMAIN / CHANNEL
    # -----------------------------------------------------

    domain = str(
        extracted_data.get(
            "contact_domain",
            "",
        )
    ).lower()

    if domain in GENERIC_DOMAINS:

        add(
            "domain_mismatch",
            (
                f"The recruiter uses a public email "
                f"provider (@{domain})."
            ),
        )

    if "telegram" in text:

        add(
            "domain_mismatch",
            (
                "The offer directs the candidate to "
                "Telegram for recruitment communication."
            ),
        )

    # -----------------------------------------------------
    # UNREALISTIC COMPENSATION
    # -----------------------------------------------------

    if any(
        phrase in text
        for phrase in [
            "75,000 per month",
            "36 lpa",
            "36,00,000",
            "5,000 per day",
            "15,000 per day",
        ]
    ):

        add(
            "salary_ratio",
            (
                "The offer contains compensation commonly "
                "associated with unrealistic entry-level "
                "or task-work claims."
            ),
        )

    # -----------------------------------------------------
    # FAKE CHECK / EQUIPMENT
    # -----------------------------------------------------

    if (
        "check" in text
        and any(
            phrase in text
            for phrase in [
                "purchase equipment",
                "purchase software",
                "buy equipment",
                "workstation",
                "office software",
            ]
        )
    ):

        add(
            "fake_check_equipment",
            (
                "The offer mentions sending a check "
                "to fund equipment or software purchases."
            ),
        )

    return evidence


# =========================================================
# TOOL 1 — RAG
# =========================================================

def check_red_flags_rag(
    offer_text: str,
    extracted_data: dict = None,
) -> list:
    """
    Evidence-grounded RAG retrieval.

    A category can only be returned when current-offer evidence
    supports that category.
    """

    extracted_data = (
        extracted_data
        or {}
    )

    observed = (
        _collect_observed_evidence(
            offer_text,
            extracted_data,
        )
    )

    if not observed:

        return []

    query_parts = []

    for action in extracted_data.get(
        "requested_actions",
        [],
    ):

        if action:

            query_parts.append(
                str(action)
            )

    for (
        category,
        evidence_items,
    ) in observed.items():

        query_parts.append(
            category.replace(
                "_",
                " ",
            )
        )

        query_parts.extend(
            evidence_items
        )

    query_string = " ".join(
        dict.fromkeys(
            query_parts
        )
    )

    query_string = re.sub(
        r"[^\w\s]",
        " ",
        query_string,
    )

    query_string = " ".join(
        query_string.split()
    )[:900]

    # -----------------------------------------------------
    # AZURE AI SEARCH
    # -----------------------------------------------------

    if (
        SEARCH_ENDPOINT
        and SEARCH_API_KEY
        and "your-search-service"
        not in SEARCH_ENDPOINT
    ):

        try:

            from azure.core.credentials import (
                AzureKeyCredential,
            )

            from azure.search.documents import (
                SearchClient,
            )

            client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(
                    SEARCH_API_KEY
                ),
                connection_timeout=5,
                read_timeout=8,
            )

            best_by_category = {}

            for (
                category,
                evidence_items,
            ) in observed.items():

                category_query_parts = [
                    category.replace(
                        "_",
                        " ",
                    ),

                    *evidence_items,

                    *[
                        str(action)
                        for action
                        in extracted_data.get(
                            "requested_actions",
                            [],
                        )
                    ],
                ]

                category_query = " ".join(
                    category_query_parts
                )

                category_query = re.sub(
                    r"[^\w\s]",
                    " ",
                    category_query,
                )

                category_query = " ".join(
                    category_query.split()
                )[:700]

                escaped_category = (
                    category.replace(
                        "'",
                        "''",
                    )
                )

                results = client.search(
                    search_text=(
                        category_query
                        if category_query
                        else "*"
                    ),

                    search_fields=[
                        "pattern",
                        "example_text",
                        "category",
                    ],

                    filter=(
                        f"category eq "
                        f"'{escaped_category}'"
                    ),

                    select=[
                        "id",
                        "category",
                        "pattern",
                        "example_text",
                        "risk_weight",
                    ],

                    top=1,
                )

                for result in results:

                    score = float(
                        result.get(
                            "@search.score",
                            0.0,
                        )
                    )

                    best_by_category[
                        category
                    ] = {
                        "id": result["id"],
                        "category": category,
                        "pattern": (
                            result["pattern"]
                        ),
                        "score": round(
                            score,
                            2,
                        ),
                        "risk_weight": (
                            result.get(
                                "risk_weight",
                                "medium",
                            )
                        ),
                        "evidence": (
                            evidence_items
                        ),
                    }

                    break

            matches = sorted(
                best_by_category.values(),
                key=lambda item: (
                    item["score"]
                ),
                reverse=True,
            )

            if matches:

                return matches[
                    :RAG_TOP_K
                ]

        except Exception as e:

            print(
                "[RAG Warning] "
                f"Azure AI Search query error: {e}. "
                "Falling back to local pattern matcher."
            )

    # -----------------------------------------------------
    # LOCAL FALLBACK
    # -----------------------------------------------------

    patterns = (
        load_cached_patterns()
    )

    best_by_category = {}

    query_words = {
        word
        for word
        in query_string
        .lower()
        .split()
        if len(word) > 3
    }

    for pattern in patterns:

        category = (
            pattern["category"]
        )

        if category not in observed:

            continue

        source = (
            f"{pattern['category']} "
            f"{pattern['pattern']} "
            f"{pattern['example_text']}"
        ).lower()

        overlap = sum(
            1
            for word in query_words
            if word in source
        )

        item = {
            "id": (
                pattern["id"]
            ),

            "category": (
                category
            ),

            "pattern": (
                pattern["pattern"]
            ),

            "score": float(
                overlap
            ),

            "risk_weight": (
                pattern.get(
                    "risk_weight",
                    "medium",
                )
            ),

            "evidence": (
                observed[
                    category
                ]
            ),
        }

        existing = (
            best_by_category.get(
                category
            )
        )

        if (
            not existing
            or item["score"]
            > existing["score"]
        ):

            best_by_category[
                category
            ] = item

    matches = sorted(
        best_by_category.values(),
        key=lambda item: (
            item["score"]
        ),
        reverse=True,
    )

    return matches[
        :RAG_TOP_K
    ]


# =========================================================
# TOOL 2 — COMPANY / DOMAIN VERIFICATION
# =========================================================

def verify_company_domain(
    company_name: str,
    contact_domain: str,
    full_email: str = "",
    offer_text: str = "",
) -> dict:
    """
    Verify recruiter-domain consistency.

    Important:
    - Non-free domains are not automatically considered verified.
    - Known companies can be checked against known domains.
    - A website explicitly provided by the recruiter is compared
      against the email domain.
    """

    company_clean = (
        company_name.strip().lower()
        if company_name
        else "not specified"
    )

    domain_clean = (
        contact_domain.strip().lower()
        if contact_domain
        else "unknown"
    )

    # -----------------------------------------------------
    # EXTRACT COMPANY WEBSITE DOMAINS
    # -----------------------------------------------------

    website_domains = []

    if offer_text:

        hosts = re.findall(
            r"https?://(?:www\.)?"
            r"([a-z0-9.-]+)",
            offer_text.lower(),
        )

        for host in hosts:

            host = host.strip(
                "."
            )

            if (
                host
                and host
                not in website_domains
            ):

                website_domains.append(
                    host
                )

    # -----------------------------------------------------
    # EMAIL DOMAIN VS WEBSITE DOMAIN
    # -----------------------------------------------------

    if (
        website_domains
        and domain_clean
        not in [
            "unknown",
            "not specified",
        ]
    ):

        exact_or_subdomain_match = any(
            (
                domain_clean == host
                or domain_clean.endswith(
                    "." + host
                )
                or host.endswith(
                    "." + domain_clean
                )
            )
            for host
            in website_domains
        )

        if not exact_or_subdomain_match:

            email_stem = (
                domain_clean
                .split(".")[0]
            )

            same_brand_other_tld = any(
                host.split(".")[0]
                == email_stem
                for host
                in website_domains
            )

            if same_brand_other_tld:

                return {
                    "status": (
                        "DOMAIN_WEBSITE_MISMATCH"
                    ),

                    "is_flagged": True,

                    "severity": (
                        "MEDIUM"
                    ),

                    "message": (
                        f"The recruiter email uses "
                        f"'@{domain_clean}', while the "
                        f"message references the company "
                        f"website '{website_domains[0]}'. "
                        "The domains are similar in name "
                        "but are not the same domain, so "
                        "ownership should be independently "
                        "verified."
                    ),
                }

    # -----------------------------------------------------
    # NO DOMAIN
    # -----------------------------------------------------

    if domain_clean in [
        "unknown",
        "not specified",
    ]:

        return {
            "status": "UNVERIFIED",
            "is_flagged": True,
            "severity": "MEDIUM",
            "message": (
                "No official recruiter contact email "
                "or domain could be identified."
            ),
        }

    # -----------------------------------------------------
    # CHAT-ONLY CHANNEL
    # -----------------------------------------------------

    if (
        "telegram" in domain_clean
        or "chat-handle" in domain_clean
        or (
            "@"
            in full_email
            and "."
            not in contact_domain
        )
    ):

        return {
            "status": (
                "SUSPICIOUS_CHANNEL"
            ),

            "is_flagged": True,

            "severity": "HIGH",

            "message": (
                "Recruiter conducts official communication "
                "solely via a chat handle without an "
                "identifiable corporate email domain."
            ),
        }

    # -----------------------------------------------------
    # FREE EMAIL PROVIDER
    # -----------------------------------------------------

    if domain_clean in GENERIC_DOMAINS:

        if company_clean not in [
            "not specified",
            "freelance",
            "individual",
        ]:

            return {
                "status": (
                    "MISMATCH_GENERIC_DOMAIN"
                ),

                "is_flagged": True,

                "severity": "HIGH",

                "message": (
                    f"Sender uses a free public email "
                    f"service (@{domain_clean}) while "
                    f"claiming to represent "
                    f"'{company_name}'. Verify the recruiter "
                    "through the organization's official "
                    "careers site or another independently "
                    "obtained contact channel."
                ),
            }

        return {
            "status": (
                "GENERIC_DOMAIN"
            ),

            "is_flagged": True,

            "severity": "MEDIUM",

            "message": (
                f"Recruiter is using a free public "
                f"email provider (@{domain_clean})."
            ),
        }

    # -----------------------------------------------------
    # SUSPICIOUS DOMAIN NAMING
    # -----------------------------------------------------

    suspicious_patterns = [
        r"-hiring",
        r"-jobs",
        r"-careers",
        r"-portal",
        r"official-",
    ]

    for pattern in suspicious_patterns:

        if re.search(
            pattern,
            domain_clean,
        ):

            return {
                "status": (
                    "POTENTIAL_SPOOFED_DOMAIN"
                ),

                "is_flagged": True,

                "severity": "HIGH",

                "message": (
                    f"Domain '@{domain_clean}' contains "
                    "a naming pattern commonly used by "
                    "unofficial recruitment domains and "
                    "should be independently verified."
                ),
            }

    # -----------------------------------------------------
    # KNOWN COMPANY CHECK
    # -----------------------------------------------------

    for (
        company_token,
        expected_domain,
    ) in KNOWN_COMPANY_DOMAINS.items():

        if company_token in company_clean:

            if (
                domain_clean
                == expected_domain
                or domain_clean.endswith(
                    "." + expected_domain
                )
            ):

                return {
                    "status": (
                        "VERIFIED_DOMAIN"
                    ),

                    "is_flagged": False,

                    "severity": "LOW",

                    "message": (
                        f"Recruiter domain "
                        f"'@{domain_clean}' matches the "
                        f"expected corporate domain for "
                        f"{company_name}."
                    ),
                }

            return {
                "status": (
                    "DOMAIN_MISMATCH"
                ),

                "is_flagged": True,

                "severity": "HIGH",

                "message": (
                    f"The claimed organization "
                    f"'{company_name}' does not match "
                    f"the expected recruiter domain "
                    f"('{expected_domain}'); the supplied "
                    f"domain is '@{domain_clean}'."
                ),
            }

    # -----------------------------------------------------
    # TEXTUAL COMPANY/DOMAIN CONSISTENCY
    # -----------------------------------------------------

    company_tokens = [
        token
        for token
        in re.findall(
            r"[a-z0-9]+",
            company_clean,
        )
        if len(token) >= 4
    ]

    domain_name = (
        domain_clean
        .split(".")[0]
    )

    if any(
        token in domain_name
        for token
        in company_tokens
    ):

        return {
            "status": (
                "PLAUSIBLE_COMPANY_DOMAIN"
            ),

            "is_flagged": False,

            "severity": "LOW",

            "message": (
                f"Domain '@{domain_clean}' is textually "
                "consistent with the claimed organization, "
                "but SafeApply has not independently "
                "verified ownership of the domain."
            ),
        }

    # -----------------------------------------------------
    # PROFESSIONAL BUT UNVERIFIED DOMAIN
    # -----------------------------------------------------

    return {
        "status": (
            "PROFESSIONAL_DOMAIN_UNVERIFIED"
        ),

        "is_flagged": False,

        "severity": "LOW",

        "message": (
            f"Domain '@{domain_clean}' is not a free "
            "email provider, but SafeApply has not "
            "independently verified that it belongs "
            f"to '{company_name}'."
        ),
    }


# =========================================================
# TOOL 3 — SALARY SANITY CHECKER
# =========================================================

def check_salary_sanity(
    salary_str: str,
    role_hint: str = "entry-level",
    offer_text: str = "",
) -> dict:
    """
    Compare compensation claims against broad sanity rules.

    This is intentionally a heuristic tool rather than a universal
    salary-verification system.
    """

    if (
        not salary_str
        or salary_str.lower()
        in [
            "not specified",
            "none",
            "unknown",
        ]
    ):

        return {
            "is_flagged": False,
            "severity": "LOW",
            "message": (
                "Salary not specified in offer text."
            ),
        }

    combined_text = (
        f"{salary_str} {offer_text}"
        .lower()
    )

    # -----------------------------------------------------
    # LPA
    # -----------------------------------------------------

    lpa_match = re.search(
        r"(\d+(?:\.\d+)?)\s?"
        r"(?:lpa|lakhs)",
        combined_text,
    )

    if lpa_match:

        value = float(
            lpa_match.group(1)
        )

        if value >= 25.0:

            return {
                "is_flagged": True,

                "severity": "HIGH",

                "claimed_salary": (
                    f"{value} LPA"
                ),

                "benchmark": (
                    "Entry-level market sanity band: "
                    "approximately ₹3 LPA - ₹10 LPA"
                ),

                "message": (
                    f"Unusually high compensation "
                    f"({value} LPA) for an entry-level "
                    "or fresher-style role warrants "
                    "additional verification."
                ),
            }

    # -----------------------------------------------------
    # MONTHLY SIMPLE TASK WORK
    # -----------------------------------------------------

    monthly_match = re.search(
        (
            r"(?:inr|rs\.?|₹)?\s?"
            r"([\d,]+)\s?"
            r"(?:per month|/month|p\.m\.)"
        ),
        combined_text,
    )

    if monthly_match:

        raw_num = (
            monthly_match.group(1)
            .replace(
                ",",
                "",
            )
        )

        try:

            num = int(
                raw_num
            )

            is_simple_task = any(
                term in combined_text
                for term in [
                    "data entry",
                    "form filling",
                    "copy paste",
                    "2 hours",
                    "part time",
                    "no experience",
                ]
            )

            if (
                is_simple_task
                and num >= 40000
            ):

                return {
                    "is_flagged": True,

                    "severity": "HIGH",

                    "claimed_salary": (
                        f"₹{num:,}/month"
                    ),

                    "benchmark": (
                        "Part-time/data-entry sanity "
                        "band: approximately "
                        "₹5,000 - ₹18,000/month"
                    ),

                    "message": (
                        f"Very high payout "
                        f"(₹{num:,}/month) is claimed "
                        "for basic task-style work."
                    ),
                }

        except ValueError:

            pass

    # -----------------------------------------------------
    # DAILY PAYOUT
    # -----------------------------------------------------

    daily_match = re.search(
        (
            r"(?:inr|rs\.?|₹)?\s?"
            r"([\d,]+)\s?"
            r"(?:per day|/day|daily)"
        ),
        combined_text,
    )

    if daily_match:

        return {
            "is_flagged": True,

            "severity": "HIGH",

            "claimed_salary": (
                daily_match.group(0)
            ),

            "message": (
                "Large daily cash or wallet-style "
                "payout claims warrant additional "
                "verification."
            ),
        }

    # -----------------------------------------------------
    # NO STRONG SALARY ANOMALY
    # -----------------------------------------------------

    return {
        "is_flagged": False,

        "severity": "LOW",

        "claimed_salary": (
            salary_str
        ),

        "message": (
            f"Compensation figure '{salary_str}' "
            "was not flagged by the current "
            "salary-sanity rules."
        ),
    }


# =========================================================
# TOOL 4 — EMSCAD ML CLASSIFIER
# =========================================================

def detect_fraud_ml(
    offer_text: str,
    extracted_data: dict = None,
) -> dict:
    """
    Run the trained EMSCAD fraud-detection model.

    The returned probability is an advisory statistical signal
    and not an independent determination of fraud.
    """

    from ml_classifier import (
        predict_job_offer,
    )

    extracted_data = (
        extracted_data
        or {}
    )

    return predict_job_offer(
        offer_text,
        metadata=extracted_data,
    )


# =========================================================
# LOCAL TEST
# =========================================================

if __name__ == "__main__":

    print(
        "Testing Tool 1 (RAG):"
    )

    res1 = check_red_flags_rag(
        (
            "Please deposit Rs 1,499 "
            "registration fee before appointment"
        )
    )

    print(
        " ",
        res1,
    )

    print(
        "\nTesting Tool 2 (Domain):"
    )

    res2 = verify_company_domain(
        "Microsoft India",
        "gmail.com",
    )

    print(
        " ",
        res2,
    )

    print(
        "\nTesting Tool 3 (Salary):"
    )

    res3 = check_salary_sanity(
        "36 LPA",
        "entry-level",
        "direct campus selection no interview",
    )

    print(
        " ",
        res3,
    )

    print(
        "\nTesting Tool 4 (ML Classifier):"
    )

    res4 = detect_fraud_ml(
        (
            "Urgent data entry work from home "
            "earn cash daily via link"
        )
    )

    print(
        " ",
        res4,
    )