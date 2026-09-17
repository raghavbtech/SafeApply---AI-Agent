"""
SafeApply - Agent Orchestration & GenAI Synthesis Layer
Coordinates extraction, tool execution, and GenAI synthesis via Azure AI Foundry / Azure OpenAI
adhering to Responsible AI principles.
"""

import os
import re
import json
from dotenv import load_dotenv
from extractor import extract_offer_details
from tools import check_red_flags_rag, verify_company_domain, check_salary_sanity

load_dotenv()

# Azure OpenAI / Foundry configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", os.getenv("FOUNDRY_ENDPOINT", ""))
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("FOUNDRY_API_KEY", ""))
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

# Option 2: GitHub Models (Azure-hosted GPT-4o-mini inference endpoint)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

RESPONSIBLE_AI_DISCLAIMER = (
    "SafeApply is an AI-powered advisory tool designed to help students identify common recruitment scam indicators. "
    "This assessment does not constitute legal advice or an absolute determination of fraud. "
    "Always independently verify employers via official corporate channels and college placement cells before sharing sensitive information or funds."
)


def is_azure_openai_configured() -> bool:
    """Check if Azure OpenAI / Foundry credentials are set."""
    return bool(
        AZURE_OPENAI_ENDPOINT
        and AZURE_OPENAI_API_KEY
        and "your-foundry-resource" not in AZURE_OPENAI_ENDPOINT
        and "your_azure_openai_api_key" not in AZURE_OPENAI_API_KEY
    )


def is_github_models_configured() -> bool:
    """Check if GitHub Models token is set for Azure-hosted model inference."""
    return bool(
        GITHUB_TOKEN
        and len(GITHUB_TOKEN.strip()) > 15
        and not GITHUB_TOKEN.startswith("your_")
    )


def is_azure_foundry_configured() -> bool:
    """Check if Azure AI Foundry / OpenAI endpoint is configured with a real key."""
    return bool(
        AZURE_OPENAI_ENDPOINT
        and AZURE_OPENAI_API_KEY
        and "your-foundry-resource" not in AZURE_OPENAI_ENDPOINT
        and "your_azure_openai_api_key" not in AZURE_OPENAI_API_KEY
    )


def is_genai_active() -> bool:
    """Check if either Azure AI Foundry, Azure OpenAI, or GitHub Models is active."""
    return is_azure_foundry_configured() or is_github_models_configured()


def _sanitize_grounded_output(parsed: dict, offer_text: str, deterministic_assessment: dict) -> dict:
    """
    Enforce evidence grounding after GenAI synthesis.

    The model may use RAG patterns for context, but unsupported sensitive-data
    claims must not be introduced into the final explanation or red-flag list.
    Risk level and score always come from the deterministic assessment.
    """
    text = offer_text.lower()

    sensitive_claims = {
        "upi pin": ["upi pin"],
        "otp": [" otp", "otp ", "one-time password", "one time password"],
        "internet banking password": [
            "internet banking password",
            "net banking password",
        ],
        "debit card": ["debit card"],
        "credit card": ["credit card"],
        "password": ["password"],
        "bank account details": [
            "bank account",
            "bank details",
            "account number",
            "ifsc",
        ],
        "aadhaar": ["aadhaar", "aadhar"],
        "pan card": ["pan card"],
        "passport": ["passport"],
    }

    unsupported = {
        claim
        for claim, aliases in sensitive_claims.items()
        if not any(alias in text for alias in aliases)
    }

    flags = parsed.get("identified_red_flags", [])
    cleaned_flags = []

    for flag in flags:
        flag_text = str(flag)
        lower_flag = flag_text.lower()

        if any(claim in lower_flag for claim in unsupported):
            continue

        cleaned_flags.append(flag_text)

    explanation = str(parsed.get("explanation", "")).strip()

    # Remove complete sentences that introduce unsupported sensitive claims.
    if explanation:
        sentences = re.split(r"(?<=[.!?])\s+", explanation)
        kept_sentences = []

        for sentence in sentences:
            lower_sentence = sentence.lower()

            if any(claim in lower_sentence for claim in unsupported):
                continue

            kept_sentences.append(sentence)

        explanation = " ".join(kept_sentences).strip()

    # If sanitization removes too much, use the deterministic explanation.
    if not explanation:
        explanation = deterministic_assessment["explanation"]

    if not cleaned_flags:
        cleaned_flags = deterministic_assessment["identified_red_flags"]

    parsed["risk_level"] = deterministic_assessment["risk_level"]
    parsed["risk_score"] = deterministic_assessment["risk_score"]
    parsed["explanation"] = explanation
    parsed["identified_red_flags"] = list(dict.fromkeys(cleaned_flags))

    return parsed


def synthesize_with_genai(
    offer_text: str,
    extracted_data: dict,
    rag_results: list,
    domain_check: dict,
    salary_check: dict,
    deterministic_assessment: dict,
) -> tuple:
    """
    Use Azure AI Foundry / Azure OpenAI / GitHub Models to explain an
    evidence-based assessment.

    The deterministic engine owns the risk score and verdict. GenAI only
    produces a grounded plain-English explanation and evidence summary.
    """
    from openai import OpenAI, AzureOpenAI

    endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/")

    if "services.ai.azure.com" in endpoint or "models.ai.azure.com" in endpoint:
        base_url = endpoint if endpoint.endswith("/models") else f"{endpoint}/models"

        client = OpenAI(
            base_url=base_url,
            api_key=AZURE_OPENAI_API_KEY,
        )

        model_name = AZURE_OPENAI_DEPLOYMENT_NAME
        mode = f"Live Azure AI Foundry ({model_name})"

    elif is_azure_openai_configured():
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )

        model_name = AZURE_OPENAI_DEPLOYMENT_NAME
        mode = f"Live Azure OpenAI ({model_name})"

    elif is_github_models_configured():
        client = OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=GITHUB_TOKEN.strip(),
        )

        model_name = "gpt-4o-mini"
        mode = "Live Azure-Hosted GitHub Models (GPT-4o-mini)"

    else:
        raise ValueError("No GenAI provider configured.")

    prompt = f"""
You are SafeApply, a recruitment-risk explanation assistant.

Your job is to EXPLAIN an evidence-based assessment.
You must not invent evidence and must not independently alter the supplied
risk verdict or risk score.

SOURCE PRIORITY:
1. ORIGINAL OFFER TEXT = primary evidence.
2. Extracted data = structured observations derived from the offer.
3. Domain and salary tool outputs = deterministic tool findings.
4. RAG results = contextual reference patterns only.

STRICT GROUNDING RULES:
- RAG documents are NOT statements about the current offer.
- A retrieved fraud pattern may contain details that do not exist in the
  current offer.
- Never transfer unsupported details from a RAG pattern into the explanation.
- Never claim that a UPI PIN, OTP, password, debit card, credit card,
  bank login, Aadhaar, PAN, passport, or payment was requested unless
  the ORIGINAL OFFER TEXT directly supports that claim.
- The word "UPI" does NOT imply "UPI PIN".
- A bank-account request does NOT imply a password, OTP, PIN, or debit-card request.
- Mention only evidence that appears in the original offer or deterministic
  tool outputs.
- If evidence is ambiguous, describe it as ambiguous.
- Do not accuse a named company of fraud. Describe the communication as
  containing patterns associated with recruitment scams.

RAG INTERPRETATION:
Each RAG result can contain:
- pattern: a knowledge-base reference pattern
- evidence: observations actually found in this offer

Use the "evidence" field when describing the CURRENT offer.
Use the "pattern" field only to explain why that evidence is relevant.

PROTECTIVE NOTICE RULE:
Statements such as "we never charge fees", "no fee is required", or
"we do not ask for money" are protective language unless the same offer
separately contains an affirmative request to pay money.

FIXED ASSESSMENT:
Risk Level: {deterministic_assessment['risk_level']}
Risk Score: {deterministic_assessment['risk_score']}/100

You MUST return those exact risk values.

ORIGINAL OFFER TEXT:
{offer_text}

EXTRACTED DATA:
{json.dumps(extracted_data, indent=2)}

RAG REFERENCE PATTERNS:
{json.dumps(rag_results, indent=2)}

DOMAIN TOOL:
{json.dumps(domain_check, indent=2)}

SALARY TOOL:
{json.dumps(salary_check, indent=2)}

Return valid JSON with exactly these keys:

{{
  "risk_level": "{deterministic_assessment['risk_level']}",
  "risk_score": {deterministic_assessment['risk_score']},
  "explanation": "<concise explanation using only grounded evidence>",
  "identified_red_flags": [
    "<directly supported flag>",
    "<directly supported flag>"
  ]
}}
"""

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are SafeApply, a Responsible AI recruitment-risk "
                    "explanation assistant. Always return valid JSON and never "
                    "introduce evidence not supported by the original offer."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )

    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content).strip()

    try:
        parsed = json.loads(content)
        parsed = _sanitize_grounded_output(
            parsed,
            offer_text,
            deterministic_assessment,
        )
        return parsed, mode

    except Exception as exc:
        print(
            f"[Agent Grounding Warning] Could not parse/sanitize GenAI JSON: {exc}. "
            "Using deterministic assessment."
        )
        return deterministic_assessment.copy(), mode


def synthesize_fallback(
    extracted_data: dict,
    rag_results: list,
    domain_check: dict,
    salary_check: dict,
) -> dict:
    """
    Deterministic evidence-based scoring engine.

    RAG contributes only when a returned match contains evidence directly
    observed in the current offer. This keeps local and cloud modes
    reproducible and prevents retrieved pattern text from becoming a factual
    claim about the offer.
    """
    risk_score = 10
    flags = []

    # 1. Evaluate grounded RAG evidence, one score contribution per category.
    seen_categories = set()

    for match in rag_results:
        category = match.get("category", "")

        if category in seen_categories:
            continue

        seen_categories.add(category)

        evidence_items = [
            str(item)
            for item in match.get("evidence", [])
            if str(item).strip()
        ]

        # Backward compatibility: older/local results may not yet include
        # evidence. In that case, do not promote the retrieved pattern text
        # into a factual red flag.
        if not evidence_items:
            continue

        if category == "upfront_fee":
            risk_score += 35
            flags.extend(evidence_items)

        elif category == "urgency_pressure":
            risk_score += 15
            flags.extend(evidence_items)

        elif category == "premature_personal_info":
            risk_score += 30
            flags.extend(evidence_items)

        elif category == "vague_role_process":
            risk_score += 15
            flags.extend(evidence_items)

        elif category == "salary_ratio":
            risk_score += 25
            flags.extend(evidence_items)

        elif category == "fake_check_equipment":
            risk_score += 35
            flags.extend(evidence_items)

        elif category == "domain_mismatch":
            # Domain scoring is handled by the dedicated domain tool below.
            # Keep the evidence for explanation without double-counting.
            flags.extend(evidence_items)

    # 2. Domain/company verification tool.
    if domain_check.get("is_flagged"):
        severity = domain_check.get("severity", "LOW")

        if severity == "HIGH":
            risk_score += 30
        elif severity == "MEDIUM":
            risk_score += 25
        else:
            risk_score += 5

        message = domain_check.get(
            "message",
            "Recruiter contact domain requires independent verification.",
        )

        if message:
            flags.append(message)

    # 3. Salary sanity checker.
    if salary_check.get("is_flagged"):
        severity = salary_check.get("severity", "LOW")

        if severity == "HIGH":
            risk_score += 25
        elif severity == "MEDIUM":
            risk_score += 15
        else:
            risk_score += 5

        message = salary_check.get(
            "message",
            "The compensation claim warrants additional verification.",
        )

        if message:
            flags.append(message)

    # 4. If extraction found suspicious actions but RAG returned no grounded
    # category, add a small caution score without inventing a stronger claim.
    if extracted_data.get("requested_actions") and not rag_results:
        risk_score += 10

        actions = [
            str(action)
            for action in extracted_data.get("requested_actions", [])[:3]
            if str(action).strip()
        ]

        if actions:
            flags.append(
                "The offer contains action requests that warrant verification: "
                + ", ".join(actions)
                + "."
            )

    unique_flags = list(dict.fromkeys(flags))
    risk_score = min(max(risk_score, 5), 98)

    if risk_score >= 65:
        verdict = "High"

        if unique_flags:
            evidence_summary = "; ".join(unique_flags[:3])
            explanation = (
                "This communication contains multiple significant recruitment-risk "
                f"indicators. Observed evidence includes: {evidence_summary}. "
                "Verify the recruiter independently before sending money, identity "
                "documents, financial information, or other sensitive data."
            )
        else:
            explanation = (
                "This communication contains multiple significant recruitment-risk "
                "indicators. Independent verification is strongly recommended before proceeding."
            )

    elif risk_score >= 35:
        verdict = "Medium"

        if unique_flags:
            evidence_summary = "; ".join(unique_flags[:2])
            explanation = (
                "This offer contains signals that warrant additional verification. "
                f"Observed evidence includes: {evidence_summary}. "
                "Confirm the recruiter through an independently obtained corporate "
                "contact or official careers portal before proceeding."
            )
        else:
            explanation = (
                "This offer contains ambiguous characteristics that warrant additional "
                "verification before proceeding."
            )

    else:
        verdict = "Low"
        explanation = (
            "No strong recruitment-scam indicators were identified by the current "
            "evidence checks. This is an advisory result, so the employer and recruiter "
            "should still be independently verified before sensitive information is shared."
        )

    return {
        "risk_level": verdict,
        "risk_score": risk_score,
        "explanation": explanation,
        "identified_red_flags": (
            unique_flags
            if unique_flags
            else ["No strong scam red flags detected by the current checks."]
        ),
    }


def analyze_job_offer(offer_text: str) -> dict:
    """
    Complete Agent Orchestration Pipeline:
    1. Input offer text -> 2. Extraction Pipeline -> 3. Agent Tool Invocations -> 4. GenAI Synthesis -> 5. Verdict
    """
    if not offer_text or len(offer_text.strip()) < 10:
        return {
            "risk_level": "Low",
            "risk_score": 0,
            "explanation": "Please provide a valid job offer text or email body for analysis.",
            "identified_red_flags": ["Insufficient text provided."],
            "extracted_data": {},
            "tool_outputs": {},
            "responsible_ai_disclaimer": RESPONSIBLE_AI_DISCLAIMER,
            "execution_mode": "Input Validation",
        }

    # Step 3: Extraction Pipeline
    extracted_data = extract_offer_details(offer_text)

    # Step 5: Execute Agent Tools
    # Tool 1: Red-Flag Pattern Checker (RAG)
    rag_results = check_red_flags_rag(offer_text, extracted_data)

    # Tool 2: Domain / Company Verification
    domain_check = verify_company_domain(
        company_name=extracted_data.get("company_name", ""),
        contact_domain=extracted_data.get("contact_domain", ""),
        full_email=extracted_data.get("contact_email", ""),
    )

    # Tool 3: Salary Sanity Checker
    salary_check = check_salary_sanity(
        salary_str=extracted_data.get("salary", ""),
        offer_text=offer_text,
    )

    # Step 6: Deterministic assessment first, then optional GenAI explanation.
    deterministic_assessment = synthesize_fallback(
        extracted_data,
        rag_results,
        domain_check,
        salary_check,
    )

    if is_genai_active():
        try:
            synthesis, mode = synthesize_with_genai(
                offer_text,
                extracted_data,
                rag_results,
                domain_check,
                salary_check,
                deterministic_assessment,
            )

        except Exception as e:
            print(
                f"[Agent Synthesis Error] GenAI call failed: {e}. "
                "Using deterministic engine."
            )

            synthesis = deterministic_assessment
            mode = "Deterministic Advisory Engine (API Fallback)"

    else:
        synthesis = deterministic_assessment
        mode = "Advisory Synthesis Engine (Local Mode)"

    return {
        "risk_level": synthesis.get("risk_level", "Medium"),
        "risk_score": synthesis.get("risk_score", 50),
        "explanation": synthesis.get("explanation", ""),
        "identified_red_flags": synthesis.get("identified_red_flags", []),
        "extracted_data": extracted_data,
        "tool_outputs": {
            "rag_matches": rag_results,
            "domain_verification": domain_check,
            "salary_sanity": salary_check,
        },
        "responsible_ai_disclaimer": RESPONSIBLE_AI_DISCLAIMER,
        "execution_mode": mode,
    }


if __name__ == "__main__":
    sample = """
    From: hr.infosys.campus@gmail.com
    Dear Candidate,
    Congratulations! You are selected as Software Engineer at Infosys India.
    Package: INR 12,00,000 per annum.
    To confirm your seat, remit INR 1,999 refundable registration fee via GooglePay within 2 hours.
    Send payment screenshot immediately.
    """
    res = analyze_job_offer(sample)
    print("\n--- SAFEAPPLY PIPELINE VERDICT ---")
    print(f"Risk Level: {res['risk_level']} (Score: {res['risk_score']}/100)")
    print(f"Mode: {res['execution_mode']}")
    print(f"Explanation: {res['explanation']}")
    print(f"Flags: {res['identified_red_flags']}")
