"""
SafeApply - Extraction Pipeline
Extracts key structured recruitment offer attributes using Azure AI Language
(Text Analytics) with high-accuracy regex heuristics and fallback support.
"""

import os
import re

from dotenv import load_dotenv

load_dotenv()


LANGUAGE_ENDPOINT = os.getenv(
    "LANGUAGE_ENDPOINT",
    "",
)

LANGUAGE_API_KEY = os.getenv(
    "LANGUAGE_API_KEY",
    "",
)


def is_azure_language_configured():
    """Check whether real Azure AI Language credentials are configured."""

    return bool(
        LANGUAGE_ENDPOINT
        and LANGUAGE_API_KEY
        and "your-language-service" not in LANGUAGE_ENDPOINT
        and "your_language_api_key" not in LANGUAGE_API_KEY
    )


# =========================================================
# EMAIL / DOMAIN
# =========================================================

def extract_email_and_domain(
    text: str,
):
    """Extract the first email address and domain."""

    email_pattern = (
        r"[a-zA-Z0-9_.+-]+@"
        r"([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
    )

    match = re.search(
        email_pattern,
        text,
    )

    if match:

        email = (
            match.group(0)
            .rstrip(".")
        )

        domain = (
            match.group(1)
            .lower()
            .rstrip(".")
        )

        return (
            email,
            domain,
        )

    # Only classify an actual @handle as Telegram/chat
    # when a conventional email address is absent.

    telegram_match = re.search(
        r"@[a-zA-Z0-9_]{4,}",
        text,
    )

    if telegram_match:

        return (
            telegram_match.group(0),
            "telegram/chat-handle",
        )

    return (
        "Not specified",
        "unknown",
    )


# =========================================================
# SALARY
# =========================================================

def normalize_compensation_number(
    number_str: str,
    suffix: str = "",
):
    """
    Convert compact compensation notation into a numeric value.

    Examples:
        5k      -> 5000
        25K     -> 25000
        0.1M    -> 100000
        1M      -> 1000000
        2.5L    -> 250000
        1Cr     -> 10000000

    Note:
        K = thousand
        M = million
        L/Lakh = 100,000
        Cr/Crore = 10,000,000
    """

    if not number_str:
        return None

    cleaned = (
        str(number_str)
        .replace(",", "")
        .strip()
    )

    try:
        value = float(cleaned)
    except ValueError:
        return None

    suffix = (
        suffix
        .strip()
        .lower()
    )

    multipliers = {
        "": 1,
        "k": 1_000,
        "m": 1_000_000,
        "l": 100_000,
        "lac": 100_000,
        "lakh": 100_000,
        "lakhs": 100_000,
        "cr": 10_000_000,
        "crore": 10_000_000,
        "crores": 10_000_000,
    }

    return (
        value
        * multipliers.get(
            suffix,
            1,
        )
    )


def extract_salary_regex(
    text: str,
):
    """
    Extract salary/compensation expressions including compact notation.

    Supported examples:
        $5k
        $5k for 2 hours
        $120k/year
        ₹25k/month
        INR 8LPA
        12 LPA
        0.1M/year
        ₹1.5L/month
        ₹1Cr/year
    """

    patterns = [
        # Currency-prefixed amounts:
        # $5k, $5k for 2 hours, $120k/year, ₹25k/month, INR 1.5L/month
        (
            r"(?:USD\s*|\$\s*|INR\s*|Rs\.?\s*|₹\s*)"
            r"\d[\d,]*(?:\.\d+)?"
            r"(?:\s?(?:k|m|l|lac|lakh|lakhs|cr|crore|crores))?"
            r"(?:\s?(?:"
            r"LPA|"
            r"per\s+hour|hourly|/hour|/hr|"
            r"per\s+day|daily|/day|"
            r"per\s+week|weekly|/week|"
            r"per\s+month|monthly|/month|p\.m\.?|"
            r"per\s+year|yearly|annually|/year|"
            r"per\s+annum|p\.a\.?"
            r"))?"
            r"(?:\s+for\s+\d+(?:\.\d+)?\s+hours?)?"
        ),

        # Number followed by Indian annual notation:
        # 8LPA, 12 LPA, 8 lakhs, 1 Cr/year
        (
            r"\d+(?:\.\d+)?\s?"
            r"(?:LPA|lakhs?|lakh|lac|L|Cr|crores?)"
            r"(?:\s?(?:per\s+annum|annually|/year))?"
        ),

        # Compact numeric form without explicit currency:
        # 0.1M/year, 120k/year
        (
            r"\d+(?:\.\d+)?\s?"
            r"(?:k|m)"
            r"(?:\s?(?:"
            r"per\s+hour|hourly|/hour|/hr|"
            r"per\s+day|daily|/day|"
            r"per\s+week|weekly|/week|"
            r"per\s+month|monthly|/month|"
            r"per\s+year|yearly|annually|/year|"
            r"per\s+annum|p\.a\.?"
            r"))?"
            r"(?:\s+for\s+\d+(?:\.\d+)?\s+hours?)?"
        ),

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:

            return (
                match.group(0)
                .strip()
            )

    return "Not specified"


def normalize_compensation_expression(
    salary_text: str,
):
    """
    Normalize compact salary notation while preserving the original period.

    Examples:
        "$5k for 2 hours" -> "$5,000 for 2 hours"
        "$120k/year"      -> "$120,000/year"
        "₹25k/month"      -> "₹25,000/month"
        "0.1M/year"       -> "100,000/year"

    This helper is primarily intended for downstream salary-sanity tools.
    """

    if (
        not salary_text
        or salary_text.lower()
        in {
            "not specified",
            "none",
            "unknown",
        }
    ):
        return salary_text

    text = salary_text.strip()

    # Handle LPA explicitly so "8LPA" becomes "800,000/year"
    # instead of treating only the leading "L" as the compact suffix.
    lpa_match = re.search(
        r"(?P<prefix>INR\s*|Rs\.?\s*|₹\s*)?"
        r"(?P<number>\d+(?:\.\d+)?)\s*LPA\b",
        text,
        re.IGNORECASE,
    )

    if lpa_match:
        value = (
            float(
                lpa_match.group("number")
            )
            * 100_000
        )

        prefix = (
            lpa_match.group("prefix")
            or ""
        )

        if float(value).is_integer():
            formatted_value = f"{int(value):,}"
        else:
            formatted_value = f"{value:,.2f}".rstrip("0").rstrip(".")

        replacement = f"{prefix}{formatted_value}/year"

        return (
            text[:lpa_match.start()]
            + replacement
            + text[lpa_match.end():]
        )

    match = re.search(
        r"(?P<prefix>USD\s*|\$\s*|INR\s*|Rs\.?\s*|₹\s*)?"
        r"(?P<number>\d[\d,]*(?:\.\d+)?)"
        r"(?:\s*(?P<suffix>k|m|l|lac|lakh|lakhs|cr|crore|crores))?",
        text,
        re.IGNORECASE,
    )

    if not match:
        return salary_text

    value = normalize_compensation_number(
        match.group("number"),
        match.group("suffix") or "",
    )

    if value is None:
        return salary_text

    prefix = (
        match.group("prefix")
        or ""
    )

    if float(value).is_integer():
        formatted_value = f"{int(value):,}"
    else:
        formatted_value = f"{value:,.2f}".rstrip("0").rstrip(".")

    replacement = f"{prefix}{formatted_value}"

    return (
        text[:match.start()]
        + replacement
        + text[match.end():]
    )


# =========================================================
# COMPANY EXTRACTION
# =========================================================

def extract_company_regex(
    text: str,
):
    """
    Extract the organization claiming to make the offer.

    Signature organization names are preferred over incidental organizations
    mentioned in the body of the message.

    Example:
        "I got your email from California State University"
    must not automatically make California State University the employer when
    the recruiter signature identifies another organization.
    """

    # -----------------------------------------------------
    # SIGNATURE FIRST
    # -----------------------------------------------------

    signature_patterns = [
        (
            r"(?im)"
            r"(?:h\.?\s*r\.?|recruiter|recruitor|"
            r"talent acquisition)"
            r"[^\n]*\n"
            r"\s*([A-Z][A-Z0-9& .-]{1,40})\s*$"
        ),

        (
            r"(?im)^"
            r"\s*([A-Z][A-Z0-9& .-]{1,40})"
            r"\s*\n"
            r"\s*(?:tel|phone|mobile)\s*:"
        ),
    ]

    for pattern in signature_patterns:

        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        company = (
            match.group(1)
            .strip(
                " .-|"
            )
        )

        if (
            company
            and company.lower()
            not in [
                "hr",
                "recruiter",
                "recruitor",
            ]
        ):

            return company

    # Explicit claimed employer in an offer; this is a claim, NOT verification.
    # Restrict to hiring context so incidental mentions are not interpreted
    # as the employer (for example, a candidate's university).
    explicit = re.search(
        r"(?i)\b(?:position|role|job|internship)\s+(?:of|as|at|with|for)\s+"
        r"[A-Za-z][A-Za-z0-9 /+&.-]{2,65}?\s+at\s+"
        r"([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,5})"
        r"(?=[\s.,;:!?\n]|$)", text,
    )
    if explicit:
        candidate = explicit.group(1).strip(' .,-')
        if candidate.lower() not in {'the company', 'our company'}:
            return candidate

    # -----------------------------------------------------
    # GENERAL BODY PATTERNS
    # -----------------------------------------------------

    patterns = [
        (
            r"(?:welcome to|joining|selected at|"
            r"recruitment for|hiring for|represent)\s+"
            r"([A-Z][A-Za-z0-9\s&]{2,30}?)"
            r"(?:\s+India|\s+Team|\s+Pvt|\s+Ltd|"
            r"\.|\n|,)"
        ),

        (
            r"(?:at|from)\s+"
            r"([A-Z][A-Za-z0-9&]{2,25}"
            r"(?:\s+[A-Z][A-Za-z0-9&]+)?)"
            r"(?:\s+HR|\s+recruitment|\s+team|\.)"
        ),

        (
            r"([A-Z][A-Za-z0-9\s&]{2,25})"
            r"\s+(?:is hiring|Talent Acquisition|"
            r"Careers|Offer Letter)"
        ),
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
        )

        if match:

            company = (
                match.group(1)
                .strip()
            )

            if (
                company.lower()
                not in [
                    "our",
                    "the company",
                    "this",
                    "dear candidate",
                    "urgent",
                ]
            ):

                return company

    return "Not specified"


# =========================================================
# REQUESTED ACTIONS
# =========================================================

def extract_action_phrases(
    text: str,
    key_phrases: list = None,
):
    """
    Extract normalized candidate actions that are actually supported
    by the submitted recruitment message.
    """

    lower_text = text.lower()

    negation_signals = [
        "no fee",
        "no fees",
        "never charges",
        "never charge",
        "does not charge",
        "will not charge",
        "never asks for money",
        "never ask for money",
        "no security deposit",
        "there is no fee",
        "free of charge",
    ]

    rules = [
        (
            "Pay registration/refundable fee",
            [
                r"\bregistration fee\b",
                r"\brefundable fee\b",
                r"\bonboarding fee\b",
                r"\bprocessing fee\b",
            ],
        ),

        (
            "Pay security deposit",
            [
                r"\bsecurity deposit\b",
                r"\brefundable deposit\b",
            ],
        ),

        (
            "Make payment via UPI",
            [
                r"\bpay\b.{0,60}\bupi\b",
                r"\bupi\b.{0,60}\bpay(?:ment)?\b",
            ],
        ),

        (
            "Send payment screenshot",
            [
                r"\bpayment screenshot\b",
                r"\btransaction screenshot\b",
                r"\bpayment proof\b",
            ],
        ),

        (
            "Provide bank account details",
            [
                r"\bbank account\b",
                r"\baccount number\b",
                r"\bifsc\b",
                r"\bbank details\b",
            ],
        ),

        (
            "Provide government ID copy",
            [
                r"\baadhaar\b",
                r"\baadhar\b",
                r"\bpan card\b",
                r"\bpassport copy\b",
            ],
        ),

        (
            "Share authentication secret",
            [
                r"\bupi pin\b",
                r"\botp\b",
                r"\bnet banking password\b",
                r"\binternet banking password\b",
            ],
        ),

        (
            "Contact via Telegram",
            [
                r"\btelegram\b",
            ],
        ),

        (
            "Contact via WhatsApp",
            [
                r"\bwhatsapp\b",
            ],
        ),

        (
            "Respond within a short deadline",
            [
                r"\bwithin\s+\d+\s+(?:minutes?|hours?)\b",
                r"\bexpires?\s+(?:today|within)\b",
                r"\bimmediately\b",
            ],
        ),

        (
            "Purchase required equipment/material",
            [
                (
                    r"\bpurchase\b.{0,80}"
                    r"\b(?:software|equipment|kit|"
                    r"handbook|laptop)\b"
                ),

                (
                    r"\bbuy\b.{0,80}"
                    r"\b(?:software|equipment|kit|"
                    r"handbook|laptop)\b"
                ),
            ],
        ),
    ]

    def is_negated(
        start: int,
        end: int,
    ) -> bool:

        context = lower_text[
            max(
                0,
                start - 90,
            ):
            min(
                len(lower_text),
                end + 90,
            )
        ]

        return any(
            signal in context
            for signal
            in negation_signals
        )

    detected = []

    for label, patterns in rules:

        for pattern in patterns:

            match = re.search(
                pattern,
                lower_text,
                re.IGNORECASE,
            )

            if not match:
                continue

            if is_negated(
                match.start(),
                match.end(),
            ):
                continue

            detected.append(
                label
            )

            break

    return list(
        dict.fromkeys(
            detected
        )
    )[:8]


# =========================================================
# MAIN EXTRACTION PIPELINE
# =========================================================

def extract_offer_details(
    offer_text: str,
) -> dict:
    """
    Main extraction pipeline.

    Combines:
    - Regex-based deterministic extraction
    - Azure AI Language NER
    - Azure AI Language key phrases
    """

    email, domain = (
        extract_email_and_domain(
            offer_text
        )
    )

    salary = (
        extract_salary_regex(
            offer_text
        )
    )

    company = (
        extract_company_regex(
            offer_text
        )
    )

    key_phrases = []

    if is_azure_language_configured():

        try:

            from azure.core.credentials import (
                AzureKeyCredential,
            )

            from azure.ai.textanalytics import (
                TextAnalyticsClient,
            )

            client = TextAnalyticsClient(
                endpoint=LANGUAGE_ENDPOINT,
                credential=AzureKeyCredential(
                    LANGUAGE_API_KEY
                ),
                connection_timeout=3,
                read_timeout=4,
            )

            # -------------------------------------------------
            # NER
            # -------------------------------------------------

            ner_result = (
                client.recognize_entities(
                    [
                        offer_text[:5000]
                    ]
                )
            )

            if (
                ner_result
                and not ner_result[0].is_error
            ):

                entities = (
                    ner_result[0]
                    .entities
                )

                for entity in entities:

                    if (
                        entity.category
                        == "Organization"
                        and company
                        == "Not specified"
                    ):

                        company = (
                            entity.text
                        )

                    elif (
                        entity.category
                        == "Quantity"
                        and entity.subcategory
                        == "Currency"
                        and salary
                        == "Not specified"
                    ):

                        salary = (
                            entity.text
                        )

            # -------------------------------------------------
            # KEY PHRASES
            # -------------------------------------------------

            kp_result = (
                client.extract_key_phrases(
                    [
                        offer_text[:5000]
                    ]
                )
            )

            if (
                kp_result
                and not kp_result[0].is_error
            ):

                key_phrases = list(
                    kp_result[0]
                    .key_phrases
                )

        except Exception as e:

            print(
                "[Azure AI Language Warning] "
                f"API call failed: {e}. "
                "Using regex fallback."
            )

    requested_actions = (
        extract_action_phrases(
            offer_text,
            key_phrases,
        )
    )

    return {
        "company_name": company,
        "salary": salary,
        "contact_email": email,
        "contact_domain": domain,
        "requested_actions": (
            requested_actions
        ),
        "key_phrases": (
            key_phrases[:8]
        ),
    }


# =========================================================
# LOCAL TEST
# =========================================================

if __name__ == "__main__":

    sample_fake = """
    Congratulations!

    You have been selected at TechCorp Solutions for Graduate Trainee.

    Annual package: ₹8,00,000/year.

    To confirm your slot, please pay a refundable registration fee
    of Rs 1,499 via UPI to verify your candidature.

    Send payment screenshot to hr.techcorp@gmail.com within 2 hours.
    """

    result = extract_offer_details(
        sample_fake
    )

    print(
        "Extraction Result:"
    )

    for key, value in result.items():

        print(
            f"  {key}: "
            f"{str(value).encode('ascii', errors='backslashreplace').decode('ascii')}"
        )