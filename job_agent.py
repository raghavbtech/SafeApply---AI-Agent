"""
SafeApply - Job Application Agent Module

Handles:
1. Structured job specification extraction from legitimate offers
2. Candidate profile matching and skill overlap scoring
3. Autonomous application package generation:
   - Tailored Cover Letter (via Azure AI Foundry / Phi-4-mini)
   - Professional Recruiter Response Email Draft
   - Quick Application Q&A
4. Human-in-the-loop application submission and audit tracking
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

APPLIED_JOBS_FILE = os.path.join(os.path.dirname(__file__), "applied_jobs.json")
PROFILE_FILE = os.path.join(os.path.dirname(__file__), "candidate_profile.json")


# =========================================================
# CANDIDATE PROFILE MANAGEMENT
# =========================================================

DEFAULT_CANDIDATE_PROFILE = {
    "full_name": "Aarav Sharma",
    "email": "aarav.sharma@example.com",
    "phone": "+91 98765 43210",
    "education": "B.Tech in Computer Science & Engineering (Final Year)",
    "university": "National Institute of Technology",
    "gpa": "8.8 / 10.0",
    "skills": [
        "Python",
        "Data Structures",
        "Algorithms",
        "Machine Learning",
        "SQL",
        "REST APIs",
        "Git",
        "Azure",
        "Docker",
        "Java",
    ],
    "experience": "Software Engineering Intern at CloudPulse (6 months) - Built scalable RESTful services in Python and Azure.",
    "preferred_roles": [
        "Software Engineer",
        "Backend Developer",
        "Machine Learning Engineer",
    ],
    "target_locations": ["Bengaluru", "Hyderabad", "Remote"],
    "portfolio_url": "https://github.com/aaravsharma-dev",
    "linkedin_url": "https://linkedin.com/in/aaravsharma",
}


def load_candidate_profile() -> Dict[str, Any]:
    """Load user candidate profile from storage or return default."""
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CANDIDATE_PROFILE.copy()
    return DEFAULT_CANDIDATE_PROFILE.copy()


def save_candidate_profile(profile: Dict[str, Any]) -> None:
    """Save updated candidate profile to storage."""
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# =========================================================
# APPLICATION TRACKER AUDIT
# =========================================================

def load_applied_jobs() -> List[Dict[str, Any]]:
    """Load applied job records from storage."""
    if os.path.exists(APPLIED_JOBS_FILE):
        try:
            with open(APPLIED_JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_applied_jobs(records: List[Dict[str, Any]]) -> None:
    """Save applied job records to storage."""
    with open(APPLIED_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# =========================================================
# JOB SPECIFICATION EXTRACTION
# =========================================================

def extract_job_spec(offer_text: str, email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract structured job attributes from an offer or recruitment message.
    """
    text = offer_text
    email_data = email_data or {}
    analysis = email_data.get("analysis") or {}
    extracted = analysis.get("extracted_data") or {}

    # Company name
    company = (
        extracted.get("company_name")
        or email_data.get("company_name")
    )
    if not company or company in ("Unknown", "Top Tech Employer"):
        comp_match = re.search(r"\b(Microsoft|Infosys|Razorpay|Google|Amazon|TCS|Wipro|Meta|Apple|TechCorp|CloudScale)\b", text, re.IGNORECASE)
        if comp_match:
            company = comp_match.group(1)
        else:
            comp_match2 = re.search(r"(?:at|at the|from|join)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\s+(?:Pvt|Ltd|Inc|Solutions|Corporation|Limited|\.|\n))", text)
            if comp_match2:
                company = comp_match2.group(1).strip()
            else:
                company = "Enterprise Employer"

    # Job title
    role = (
        extracted.get("job_title")
        or email_data.get("role_title")
    )
    if not role or role in ("Not Specified", "Software Engineer"):
        role_match = re.search(r"(?:role(?:\s+of)?|position|internship as|selected as)\s*[:\-]?\s*([A-Za-z\s\-]+?)(?:\s+at|\.|\n|,)", text, re.IGNORECASE)
        if role_match:
            role = role_match.group(1).strip()
        else:
            role = "Software Engineer"

    # Location
    location = "Bengaluru / Hyderabad / Hybrid"
    loc_match = re.search(r"\b(?:location|campus|centre|centre at|at|in)\s*:\s*([A-Za-z\s,]+)", text, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(1).split("\n")[0].strip()
    elif "hyderabad" in text.lower():
        location = "Hyderabad Campus"
    elif "mysore" in text.lower():
        location = "Mysore Development Centre"
    elif "bengaluru" in text.lower() or "bangalore" in text.lower():
        location = "Bengaluru (Hybrid)"

    # Salary or Stipend
    salary = "Competitive Industry Standard"
    sal_match = re.search(r"\b(?:ctc|stipend|compensation|salary|payout)\s*:\s*([^\n\.,]+)", text, re.IGNORECASE)
    if sal_match:
        salary = sal_match.group(1).strip()

    # Skills detection
    common_skills = [
        "Python", "Java", "C++", "JavaScript", "TypeScript", "Go", "Rust",
        "Data Structures", "Algorithms", "Machine Learning", "SQL", "NoSQL",
        "REST APIs", "Microservices", "Docker", "Kubernetes", "Azure", "AWS",
        "Git", "Problem Solving", "Cloud Fundamentals", "React", "Node.js"
    ]
    detected_skills = []
    for skill in common_skills:
        if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE):
            detected_skills.append(skill)

    if not detected_skills:
        detected_skills = ["Python", "Data Structures", "Algorithms", "Problem Solving"]

    # Application portal or URL
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    portal_url = urls[0] if urls else "Official Careers Portal"

    # Contact email
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    contact_email = emails[0] if emails else email_data.get("sender", "careers@company.com")

    return {
        "company_name": company,
        "role_title": role,
        "location": location,
        "salary": salary,
        "required_skills": detected_skills,
        "portal_url": portal_url,
        "contact_email": contact_email,
        "raw_text": offer_text,
    }


# =========================================================
# PROFILE MATCHING ENGINE
# =========================================================

def evaluate_candidate_match(
    job_spec: Dict[str, Any],
    candidate_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compare job requirements against candidate profile.
    Computes profile match percentage, matched skills, and missing skills.
    """
    profile = candidate_profile or load_candidate_profile()
    candidate_skills = set(s.lower() for s in profile.get("skills", []))
    required_skills = job_spec.get("required_skills", [])

    matched = []
    missing = []

    for req in required_skills:
        # Check direct or substring match
        req_lower = req.lower()
        if any(req_lower == cs or req_lower in cs or cs in req_lower for cs in candidate_skills):
            matched.append(req)
        else:
            missing.append(req)

    total_req = max(len(required_skills), 1)
    match_pct = int(round((len(matched) / total_req) * 100))

    if match_pct >= 75:
        match_rating = "Strong Match"
        match_badge_color = "#22c55e"
    elif match_pct >= 50:
        match_rating = "Moderate Match"
        match_badge_color = "#f59e0b"
    else:
        match_rating = "Stretch Opportunity"
        match_badge_color = "#3b82f6"

    return {
        "match_percentage": match_pct,
        "match_rating": match_rating,
        "match_badge_color": match_badge_color,
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": len(required_skills),
        "candidate_skills_count": len(candidate_skills),
    }


# =========================================================
# APPLICATION PACKAGE GENERATION (GENAI + FALLBACK)
# =========================================================

def generate_application_package(
    job_spec: Dict[str, Any],
    candidate_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """
    Generate tailored cover letter, recruiter reply draft, and application talking points.
    Uses Azure AI Foundry (Phi-4-mini / Azure OpenAI) if configured, with robust fallback template.
    """
    profile = candidate_profile or load_candidate_profile()
    match_eval = evaluate_candidate_match(job_spec, profile)

    company = job_spec.get("company_name", "the company")
    role = job_spec.get("role_title", "Software Engineer")
    cand_name = profile.get("full_name", "Aarav Sharma")
    cand_email = profile.get("email", "aarav.sharma@example.com")
    cand_phone = profile.get("phone", "+91 98765 43210")
    cand_univ = profile.get("university", "National Institute of Technology")
    cand_degree = profile.get("education", "B.Tech Computer Science")
    cand_exp = profile.get("experience", "")
    matched_skills_str = ", ".join(match_eval["matched_skills"]) or "Python, Problem Solving"

    # Try calling Azure AI Foundry for GenAI generated cover letter
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", os.getenv("FOUNDRY_ENDPOINT", ""))
    api_key = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("FOUNDRY_API_KEY", ""))
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "Phi-4-mini-instruct")

    cover_letter = None
    recruiter_reply = None

    if endpoint and api_key and "your-foundry-resource" not in endpoint:
        try:
            from openai import OpenAI

            base_url = endpoint if endpoint.endswith("/models") else f"{endpoint}/models"
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=12.0)

            prompt = f"""You are an elite career advisor and AI job application assistant.
Generate a tailored, professional, and compelling application package for candidate {cand_name} applying for '{role}' at '{company}'.

Candidate Details:
- Education: {cand_degree}, {cand_univ}
- Relevant Skills: {matched_skills_str}
- Experience: {cand_exp}
- Contact: {cand_email} | {cand_phone}

Job Details:
- Company: {company}
- Role: {role}
- Required Skills: {', '.join(job_spec.get('required_skills', []))}
- Location: {job_spec.get('location', 'India')}

Produce valid JSON with exactly two fields:
1. "cover_letter": A 3-paragraph professional cover letter highlighting the candidate's exact matched skills and internship achievements.
2. "recruiter_reply": A concise, polite, and confident email reply (under 150 words) to the hiring manager expressing enthusiasm, confirming availability, and stating that the resume is attached.

Return only valid JSON. Do not include markdown code ticks.
"""

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You are a professional recruitment assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
            )

            content = response.choices[0].message.content.strip()
            # Parse JSON
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            parsed = json.loads(content)
            cover_letter = parsed.get("cover_letter")
            recruiter_reply = parsed.get("recruiter_reply")

        except Exception:
            pass  # Gracefully fall through to deterministic template

    # High quality fallback template if GenAI was offline or timed out
    if not cover_letter:
        cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my enthusiastic interest in the {role} opportunity at {company}. With a background in {cand_degree} from {cand_univ} and hands-on experience in {matched_skills_str}, I am excited about the prospect of contributing to your engineering initiatives.

During my previous work, {cand_exp} This experience taught me how to write robust, maintainable code, collaborate effectively with cross-functional teams, and deliver solutions under tight timelines. Having reviewed the role requirements, I am confident that my technical grounding in {matched_skills_str} directly aligns with {company}'s standards.

I would welcome the opportunity to discuss how my technical skills and enthusiasm can add immediate value to your team. Thank you for your time and consideration.

Sincerely,
{cand_name}
{cand_email} | {cand_phone}
{profile.get('linkedin_url', '')}"""

    if not recruiter_reply:
        recruiter_reply = f"""Subject: Re: Application for {role} - {cand_name}

Dear {company} Talent Acquisition Team,

Thank you for reaching out regarding the {role} position at {company}. I am very excited about this opportunity and would love to proceed with the next steps in your recruitment process.

As requested, I have attached my updated resume detailing my background in {matched_skills_str} and relevant project experience. Please let me know if you require any additional information or documentation.

I look forward to speaking with the team soon.

Warm regards,
{cand_name}
{cand_phone} | {cand_email}"""

    qa_talking_points = f"""• **Why {company}?** Inspired by {company}'s technological impact and engineering culture.
• **Core Competency:** Strong practical mastery of {matched_skills_str}.
• **Availability:** Available immediately for technical evaluation and interviews.
• **Notice Period / Joining:** 15–30 days or immediate upon graduation."""

    return {
        "cover_letter": cover_letter,
        "recruiter_reply": recruiter_reply,
        "qa_talking_points": qa_talking_points,
    }


# =========================================================
# SUBMISSION RECORDING
# =========================================================

def submit_application(
    email_id: str,
    job_spec: Dict[str, Any],
    application_package: Dict[str, str],
    candidate_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record an approved application submission in the audit log.
    Marks the job as applied with timestamp and tracking ID.
    """
    records = load_applied_jobs()
    profile = candidate_profile or load_candidate_profile()

    submission_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{job_spec.get('company_name', 'JOB')[:3].upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    record = {
        "submission_id": submission_id,
        "email_id": email_id,
        "company_name": job_spec.get("company_name", "Unknown"),
        "role_title": job_spec.get("role_title", "Software Engineer"),
        "applied_at": timestamp,
        "candidate_name": profile.get("full_name"),
        "candidate_email": profile.get("email"),
        "portal_url": job_spec.get("portal_url"),
        "recruiter_email": job_spec.get("contact_email"),
        "cover_letter_snippet": application_package.get("cover_letter", "")[:200] + "...",
        "recruiter_reply": application_package.get("recruiter_reply"),
        "status": "Submitted / Active",
    }

    records.insert(0, record)
    save_applied_jobs(records)
    return record
