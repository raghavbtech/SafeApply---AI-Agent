"""
SafeApply - Extraction Pipeline
Extracts key structured recruitment offer attributes using Azure AI Language
(Text Analytics) with high-accuracy regex heuristics and fallback support.
"""

import os
import re
from dotenv import load_dotenv

load_dotenv()

LANGUAGE_ENDPOINT = os.getenv("LANGUAGE_ENDPOINT", "")
LANGUAGE_API_KEY = os.getenv("LANGUAGE_API_KEY", "")


def is_azure_language_configured():
    """Check whether real Azure AI Language credentials are configured."""
    return bool(
        LANGUAGE_ENDPOINT
        and LANGUAGE_API_KEY
        and "your-language-service" not in LANGUAGE_ENDPOINT
        and "your_language_api_key" not in LANGUAGE_API_KEY
    )


def extract_email_and_domain(text: str):
    """Extract first email address and domain using robust regex."""
    # Look for standard email pattern
    email_pattern = r'[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
    match = re.search(email_pattern, text)
    if match:
        email = match.group(0).rstrip('.')
        domain = match.group(1).lower().rstrip('.')
        return email, domain

    # Check for Telegram/WhatsApp handles if email is absent
    telegram_match = re.search(r'@[a-zA-Z0-9_]{4,}', text)
    if telegram_match:
        return telegram_match.group(0), "telegram/chat-handle"

    return "Not specified", "unknown"


def extract_salary_regex(text: str):
    """Extract salary figures using standard Indian & international currency patterns."""
    patterns = [
        r'(?:INR|Rs\.?|₹)\s?[\d,]+(?:\s?-\s?[\d,]+)?(?:\s?(?:LPA|per month|p\.m\.|per annum|/month|/year|lakhs?))?',
        r'\d+(?:\.\d+)?\s?(?:LPA|Lakhs?(?:\s?per annum)?)',
        r'\$\s?[\d,]+(?:\s?(?:per month|/month|/year|per annum|p\.a\.))?',
        r'[\d,]+\s?(?:INR|Rs\.?|₹)(?:\s?per month|/month)?',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0).strip()
    return "Not specified"


def extract_company_regex(text: str):
    """Heuristic extraction of company name from common offer phrasing."""
    patterns = [
        r'(?:welcome to|joining|selected at|recruitment for|hiring for|represent)\s+([A-Z][A-Za-z0-9\s&]{2,30}?)(?:\s+India|\s+Team|\s+Pvt|\s+Ltd|\.|\n|,)',
        r'(?:at|from)\s+([A-Z][A-Za-z0-9&]{2,25}(?:\s+[A-Z][A-Za-z0-9&]+)?)(?:\s+HR|\s+recruitment|\s+team|\.)',
        r'([A-Z][A-Za-z0-9\s&]{2,25})\s+(?:is hiring|Talent Acquisition|Careers|Offer Letter)',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            comp = m.group(1).strip()
            # Filter out generic words
            if comp.lower() not in ["our", "the company", "this", "dear candidate", "urgent"]:
                return comp
    return "Not specified"


def extract_action_phrases(text: str, key_phrases: list = None):
    """
    Extract normalized candidate actions directly supported by the offer text.

    These values are intentionally concise because they are consumed by both
    the UI and the RAG query builder.
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
            [r"\btelegram\b"],
        ),
        (
            "Contact via WhatsApp",
            [r"\bwhatsapp\b"],
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
                r"\bpurchase\b.{0,80}\b(?:software|equipment|kit|handbook|laptop)\b",
                r"\bbuy\b.{0,80}\b(?:software|equipment|kit|handbook|laptop)\b",
            ],
        ),
    ]

    def is_negated(start: int, end: int) -> bool:
        context = lower_text[max(0, start - 90):min(len(lower_text), end + 90)]
        return any(signal in context for signal in negation_signals)

    detected = []

    for label, patterns in rules:
        for pattern in patterns:
            match = re.search(pattern, lower_text, re.IGNORECASE)
            if not match:
                continue

            if is_negated(match.start(), match.end()):
                continue

            detected.append(label)
            break

    return list(dict.fromkeys(detected))[:8]


def extract_offer_details(offer_text: str) -> dict:
    """
    Main extraction pipeline.
    Combines Azure AI Language (NER + Key Phrases) when configured with regex fallbacks.
    """
    email, domain = extract_email_and_domain(offer_text)
    salary = extract_salary_regex(offer_text)
    company = extract_company_regex(offer_text)
    key_phrases = []

    # Use Azure AI Language if configured
    if is_azure_language_configured():
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.textanalytics import TextAnalyticsClient

            client = TextAnalyticsClient(
                endpoint=LANGUAGE_ENDPOINT,
                credential=AzureKeyCredential(LANGUAGE_API_KEY),
                connection_timeout=3,
                read_timeout=4,
            )

            # NER
            ner_result = client.recognize_entities([offer_text[:5000]])
            if ner_result and not ner_result[0].is_error:
                entities = ner_result[0].entities
                for ent in entities:
                    if ent.category == "Organization" and company == "Not specified":
                        company = ent.text
                    elif ent.category == "Quantity" and ent.subcategory == "Currency" and salary == "Not specified":
                        salary = ent.text

            # Key Phrases
            kp_result = client.extract_key_phrases([offer_text[:5000]])
            if kp_result and not kp_result[0].is_error:
                key_phrases = list(kp_result[0].key_phrases)

        except Exception as e:
            print(f"[Azure AI Language Warning] API call failed: {e}. Using regex fallback.")

    requested_actions = extract_action_phrases(offer_text, key_phrases)

    return {
        "company_name": company,
        "salary": salary,
        "contact_email": email,
        "contact_domain": domain,
        "requested_actions": requested_actions,
        "key_phrases": key_phrases[:8],
    }


if __name__ == "__main__":
    sample_fake = """
    Congratulations! You have been selected at TechCorp Solutions for Graduate Trainee.
    Annual package: ₹8,00,000/year.
    To confirm your slot, please pay a refundable registration fee of Rs 1,499 via UPI to verify your candidature.
    Send payment screenshot to hr.techcorp@gmail.com within 2 hours.
    """
    result = extract_offer_details(sample_fake)
    print("Extraction Result:")
    for k, v in result.items():
        print(f"  {k}: {str(v).encode('ascii', errors='backslashreplace').decode('ascii')}")
