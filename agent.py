"""
SafeApply - Agent Orchestration & GenAI Synthesis Layer
Coordinates extraction, tool execution, and GenAI synthesis via Azure AI Foundry / Azure OpenAI
adhering to Responsible AI principles.
"""

import os
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


def synthesize_with_azure_openai(extracted_data: dict, rag_results: list, domain_check: dict, salary_check: dict) -> dict:
    """Synthesize results using Azure AI Foundry / Azure OpenAI GPT model."""
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )

    prompt = f"""You are a recruitment fraud risk assessor. Given the following extracted job offer
details and analysis results, provide a risk verdict (Low/Medium/High) and a clear,
plain-English explanation citing specific red flags. Be advisory, not definitive.
Do not make absolute accusations against any named company.

Extracted data:
{json.dumps(extracted_data, indent=2)}

Matched scam patterns (RAG):
{json.dumps(rag_results, indent=2)}

Domain check result:
{json.dumps(domain_check, indent=2)}

Salary check result:
{json.dumps(salary_check, indent=2)}

Respond strictly in valid JSON format with these exact keys:
{{
  "risk_level": "Low" | "Medium" | "High",
  "risk_score": <integer from 0 to 100>,
  "explanation": "<plain-English reasoning citing specific red flags>",
  "identified_red_flags": ["<flag 1>", "<flag 2>"]
}}
"""

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are SafeApply, a Responsible AI recruitment scam detector. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    try:
        parsed = json.loads(content)
        return parsed
    except Exception:
        return {
            "risk_level": "Medium",
            "risk_score": 50,
            "explanation": content,
            "identified_red_flags": ["Automated extraction completed, manual review advised."]
        }


def synthesize_fallback(extracted_data: dict, rag_results: list, domain_check: dict, salary_check: dict) -> dict:
    """
    Deterministic synthesis fallback engine used when Azure OpenAI credentials
    are not yet active, ensuring seamless local offline evaluation.
    """
    risk_score = 10
    flags = []

    # 1. Evaluate RAG matches grouped by unique fraud category
    seen_categories = set()
    for match in rag_results:
        cat = match.get("category", "")
        if cat in seen_categories:
            continue
        seen_categories.add(cat)

        weight = match.get("risk_weight", "medium")
        if cat == "upfront_fee":
            risk_score += 45
            flags.append(f"Advance Fee Pattern: {match['pattern']}")
        elif cat == "urgency_pressure":
            risk_score += 20
            flags.append(f"Urgency / Pressure Tactic: {match['pattern']}")
        elif cat == "premature_personal_info":
            risk_score += 35
            flags.append(f"Sensitive Data Request: {match['pattern']}")
        elif cat == "vague_role_process":
            risk_score += 20
            flags.append(f"Vague Selection: {match['pattern']}")
        elif cat == "salary_ratio":
            risk_score += 25
            flags.append(f"Suspicious Salary: {match['pattern']}")
        elif weight == "high":
            risk_score += 25
            flags.append(f"Matched Fraud Indicator: {match['pattern']}")

    # 2. Evaluate Domain Verification Tool
    if domain_check.get("is_flagged"):
        if domain_check.get("severity") == "HIGH":
            risk_score += 35
            flags.append(domain_check.get("message", "Suspicious or generic recruiter email domain."))
        else:
            risk_score += 25
            flags.append(domain_check.get("message", "Generic email service used."))

    # 3. Evaluate Salary Sanity Tool
    if salary_check.get("is_flagged"):
        if salary_check.get("severity") == "HIGH":
            risk_score += 30
            flags.append(salary_check.get("message", "Disproportionate compensation offer."))
        else:
            risk_score += 15
            flags.append(salary_check.get("message", "Unusual salary structure."))

    # 4. Check unverified requested actions
    if extracted_data.get("requested_actions") and not rag_results:
        risk_score += 15
        flags.append(f"Contains urgent or specific action requests: {', '.join([a.split(' ')[0] for a in extracted_data['requested_actions'][:2]])}")

    # Deduplicate flags
    unique_flags = list(dict.fromkeys(flags))

    # Cap score
    risk_score = min(max(risk_score, 5), 98)

    # Verdict assignment
    if risk_score >= 60:
        verdict = "High"
        explanation = (
            f"This communication exhibits multiple significant indicators commonly associated with recruitment fraud. "
            f"Specifically: {'; '.join(unique_flags[:3])}. Legitimate employers do not request advance payments, "
            f"personal banking credentials, or recruit exclusively through unverified channels."
        )
    elif risk_score >= 35:
        verdict = "Medium"
        explanation = (
            f"This offer displays ambiguous characteristics that warrant caution. "
            f"Identified signals include: {'; '.join(unique_flags[:2])}. Candidates are advised to contact the company's "
            f"official HR department or career portal before proceeding."
        )
    else:
        verdict = "Low"
        explanation = (
            "No common recruitment scam indicators were identified. The offer exhibits standard corporate communication patterns, "
            "verified contact domains, and does not solicit fees or premature sensitive credentials."
        )

    return {
        "risk_level": verdict,
        "risk_score": risk_score,
        "explanation": explanation,
        "identified_red_flags": unique_flags if unique_flags else ["No scam red flags detected."]
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

    # Step 6: GenAI Synthesis Layer
    if is_azure_openai_configured():
        try:
            synthesis = synthesize_with_azure_openai(extracted_data, rag_results, domain_check, salary_check)
            mode = "Live Azure AI Foundry (GPT-4o-mini)"
        except Exception as e:
            print(f"[Agent Synthesis Error] Azure OpenAI call failed: {e}. Using deterministic engine.")
            synthesis = synthesize_fallback(extracted_data, rag_results, domain_check, salary_check)
            mode = "Deterministic Advisory Engine (API Fallback)"
    else:
        synthesis = synthesize_fallback(extracted_data, rag_results, domain_check, salary_check)
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
