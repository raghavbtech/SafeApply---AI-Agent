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


def synthesize_with_genai(extracted_data: dict, rag_results: list, domain_check: dict, salary_check: dict) -> tuple:
    """Synthesize results using Azure AI Foundry (Phi-4-mini-instruct / GPT) or Azure OpenAI."""
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

    prompt = f"""You are a recruitment fraud risk assessor. Given the following extracted job offer
details and analysis results, provide a risk verdict (Low/Medium/High) and a clear,
plain-English explanation citing specific red flags. Be advisory, not definitive.
Do not make absolute accusations against any named company.

CRITICAL RESPONSIBLE AI EVALUATION RULES:
1. PROTECTIVE DISCLAIMERS: If the offer states that the company "never charges any fee", "does not ask for money", or "no fee is required", this is a legitimate corporate anti-fraud notice, NOT an upfront fee solicitation! Do NOT flag it as a scam.
2. LEGITIMATE OFFERS: If domain_verification is "VERIFIED_DOMAIN" (e.g. microsoft.com, infosys.com, razorpay.com) and no upfront payments or sensitive banking data are demanded, the risk_level MUST be "Low" (risk_score <= 25).
3. HIGH RISK OFFERS: Assign "High" risk ONLY when there is clear affirmative fraud: candidate is required to pay fees/deposits (via UPI/transfer), upload unredacted Aadhaar/debit cards, or contact exclusively via unverified Telegram/chat handles.
4. AMBIGUOUS OFFERS: Assign "Medium" risk (risk_score strictly between 30 and 55) if an informal recruiter uses generic email (@gmail/@yahoo) or short deadline, but does NOT ask for money or passwords. Do NOT assign High risk.

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
        model=model_name,
        messages=[
            {"role": "system", "content": "You are SafeApply, a Responsible AI recruitment scam detector. Always return valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    content = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content).strip()

    try:
        parsed = json.loads(content)
        verdict = str(parsed.get("risk_level", "Medium")).strip().capitalize()
        if "High" in verdict:
            verdict = "High"
        elif "Low" in verdict:
            verdict = "Low"
        else:
            verdict = "Medium"
        parsed["risk_level"] = verdict

        # Align numerical score consistently with verdict
        raw_score = int(float(parsed.get("risk_score", 50)))
        if verdict == "High":
            parsed["risk_score"] = max(70, raw_score)
        elif verdict == "Low":
            parsed["risk_score"] = min(20, raw_score) if raw_score > 0 else 10
        else:
            parsed["risk_score"] = raw_score if 30 <= raw_score <= 60 else 45

        return parsed, mode
    except Exception:
        return {
            "risk_level": "Medium",
            "risk_score": 50,
            "explanation": content,
            "identified_red_flags": ["Automated extraction completed, manual review advised."]
        }, mode


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
    if is_genai_active():
        try:
            synthesis, mode = synthesize_with_genai(extracted_data, rag_results, domain_check, salary_check)
        except Exception as e:
            print(f"[Agent Synthesis Error] GenAI call failed: {e}. Using deterministic engine.")
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
