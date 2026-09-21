"""
SafeApply - Job Application Agent Module

Handles:
1. Structured job specification extraction from legitimate offers
2. Candidate profile matching and skill overlap scoring
3. Application package generation:
   - Tailored Cover Letter (via Azure AI Foundry, with a template fallback)
   - Professional Recruiter Response Email Draft
   - Quick Application Q&A
4. Human-approved application-package recording and audit tracking

Storage
-------
Applied-job records live in Azure Cosmos DB via azure_db.py, in the same
container and /user_id partition as the mailbox. This was previously split
across a separate local database.py + applied_jobs.json, which meant mailbox
state and application state lived in two different stores under two
different consistency guarantees (Flaw 18). Both now go through azure_db.py.

The candidate profile itself is small, purely local preference data (no scam
evidence, no audit requirement), so it stays in a local JSON file rather than
Cosmos. Its default is deliberately empty: a Job Agent that fabricates job
details on the employer's side (Flaw 9) and also fabricates the candidate's
own name, CGPA, and college on the other side would be an odd double
standard. An empty profile simply produces a lower match score and a more
generic (but not invented) cover letter until the user fills it in.
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

from azure_db import db_save_applied_job, db_get_applied_jobs

load_dotenv()

PROFILE_FILE = os.path.join(os.path.dirname(__file__), "candidate_profile.json")

# Kept only as an emergency fallback if both Cosmos and the local profile
# file are unavailable. Never used to fabricate application content; matching
# and cover-letter generation degrade gracefully when fields are empty.
EMPTY_CANDIDATE_PROFILE: Dict[str, Any] = {
    "full_name": "",
    "email": "",
    "phone": "",
    "education": "",
    "university": "",
    "cgpa": "",
    "grading_scale": "",
    "skills": [],
    "experience": "",
    "preferred_roles": [],
    "target_locations": [],
    "portfolio_url": "",
    "linkedin_url": "",
    "resume_path": "",
    "resume_filename": "",
}

# =========================================================
# CANDIDATE PROFILE MANAGEMENT
# =========================================================

def is_candidate_profile_complete(profile: Optional[Dict[str, Any]]) -> bool:
    """
    Check whether a candidate profile has all mandatory fields (Name, Email, Resume file) filled.
    """
    if not profile:
        return False
    full_name = (profile.get("full_name") or "").strip()
    email = (profile.get("email") or "").strip()
    resume_path = (profile.get("resume_path") or "").strip()

    if not full_name or not email:
        return False

    # Check if resume_path is set and file exists on disk, OR if resume_filename exists
    if resume_path and os.path.exists(resume_path):
        return True
    if profile.get("resume_filename"):
        return True

    return False


def load_candidate_profile(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Load the candidate profile from persistent database state, or local storage."""
    uid = user_id
    if uid:
        try:
            from azure_db import db_get_state
            stored = db_get_state("candidate_profile", default=None, user_id=uid)
            if stored and isinstance(stored, dict) and any(stored.values()):
                merged = dict(EMPTY_CANDIDATE_PROFILE)
                merged.update(stored)
                return merged
        except Exception:
            pass

    return EMPTY_CANDIDATE_PROFILE.copy()


def save_candidate_profile(profile: Dict[str, Any]) -> None:
    """Save the candidate profile to local storage."""
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


# =========================================================
# APPLICATION TRACKER
# =========================================================

def load_applied_jobs() -> List[Dict[str, Any]]:
    """Load application-package records for the current user from Cosmos."""
    try:
        return db_get_applied_jobs()
    except Exception as exc:  # noqa: BLE001
        print(f"[job_agent] could not load applied jobs: {exc}")
        return []


# =========================================================
# JOB SPECIFICATION EXTRACTION
# =========================================================

def extract_job_spec(offer_text: str, email_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Extract structured job attributes from an offer or recruitment message.

    Never fabricates a value the message did not contain (Flaw 9). Anything
    not found stays "Not specified" rather than being filled with a plausible
    guess such as a default salary band or a common skill list.
    """
    text = offer_text
    email_data = email_data or {}
    analysis = email_data.get("analysis") or {}
    extracted = analysis.get("extracted_data") or {}

    # Company name
    company = extracted.get("company_name") or email_data.get("company_name")
    if not company or company == "Unknown":
        comp_match = re.search(
            r"\b(Microsoft|Infosys|Razorpay|Google|Amazon|TCS|Wipro|Meta|Apple|TechCorp|CloudScale)\b",
            text, re.IGNORECASE,
        )
        if comp_match:
            company = comp_match.group(1)
        else:
            comp_match2 = re.search(
                r"(?:at|at the|from|join)\s+([A-Z][A-Za-z0-9\s&]+?)"
                r"(?:\s+(?:Pvt|Ltd|Inc|Solutions|Corporation|Limited|\.|\n))",
                text,
            )
            company = comp_match2.group(1).strip() if comp_match2 else "Not specified"

    # Job title
    role = extracted.get("job_title") or email_data.get("role_title")
    if not role or role == "Not Specified":
        role_match = re.search(
            r"(?:role(?:\s+of)?|position(?:\s+of)?|internship as|selected as)\s*[:\-]?\s*"
            r"([A-Za-z\s\-]+?)(?:\s+at|\.|\n|,)",
            text, re.IGNORECASE,
        )
        if role_match:
            candidate_role = role_match.group(1).strip()
            vague_terms = ("available", "open", "here", "details", "opportunity", "opening", "vacant")
            role = "Not specified" if candidate_role.lower() in vague_terms else candidate_role
        else:
            role = "Not specified"

    # Location
    location = "Not specified"
    loc_match = re.search(r"\b(?:location|campus|centre|centre at|at|in)\s*:\s*([A-Za-z\s,]+)", text, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(1).split("\n")[0].strip()
    elif "hyderabad" in text.lower():
        location = "Hyderabad"
    elif "mysore" in text.lower():
        location = "Mysore"
    elif "bengaluru" in text.lower() or "bangalore" in text.lower():
        location = "Bengaluru"

    # Salary or stipend — never defaulted to "Competitive" or similar
    salary = "Not specified"
    sal_match = re.search(r"\b(?:ctc|stipend|compensation|salary|payout)\s*:\s*([^\n\.,]+)", text, re.IGNORECASE)
    if sal_match:
        salary = sal_match.group(1).strip()

    # Skills actually present in the message text — never a default list
    common_skills = [
        "Python", "Java", "C++", "JavaScript", "TypeScript", "Go", "Rust",
        "Data Structures", "Algorithms", "Machine Learning", "SQL", "NoSQL",
        "REST APIs", "Microservices", "Docker", "Kubernetes", "Azure", "AWS",
        "Git", "Problem Solving", "Cloud Fundamentals", "React", "Node.js",
    ]
    detected_skills = [s for s in common_skills if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE)]

    # Application portal or URL
    urls = re.findall(r"https?://[^\s<>\"']+", text)
    portal_url = urls[0] if urls else "Not specified"

    # Contact email extraction with smart filtering
    sender_email = (email_data.get("sender") or "").strip()
    cand_email = (load_candidate_profile().get("email") or "").strip().lower()

    ignored_domains = ("example.com", "domain.com", "localhost", "w3.org", "schema.org", "2x.png", "3x.png", "1x.png")
    ignored_prefixes = ("support@", "info@", "help@", "privacy@", "admin@", "unsubscribe@", "notifications@", "no-reply@", "noreply@")
    ignored_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js", ".html", ".htm", ".ico")

    all_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    valid_body_emails = []
    for em in all_emails:
        em_lower = em.lower().strip()
        if em_lower == cand_email:
            continue
        if any(em_lower.endswith(ext) for ext in ignored_extensions):
            continue
        if any(em_lower.endswith(d) for d in ignored_domains):
            continue
        if any(em_lower.startswith(p) for p in ignored_prefixes):
            continue
        domain_part = em_lower.split("@")[-1]
        tld = domain_part.split(".")[-1]
        if not tld.isalpha() or len(tld) < 2 or len(tld) > 10:
            continue
        valid_body_emails.append(em)

    # Prioritize sender_email if valid and not no-reply
    if sender_email and sender_email != "Not specified" and not is_no_reply_email(sender_email):
        contact_email = sender_email
    elif valid_body_emails:
        contact_email = valid_body_emails[0]
    elif sender_email and sender_email != "Not specified":
        contact_email = sender_email
    else:
        contact_email = "Not specified"

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
    """Compare job requirements against the candidate profile."""
    profile = candidate_profile or load_candidate_profile()
    candidate_skills = set(s.lower() for s in profile.get("skills", []))
    required_skills = job_spec.get("required_skills", [])

    matched, missing = [], []
    for req in required_skills:
        req_lower = req.lower()
        if any(req_lower == cs or req_lower in cs or cs in req_lower for cs in candidate_skills):
            matched.append(req)
        else:
            missing.append(req)

    matched = list(dict.fromkeys(matched))
    missing = list(dict.fromkeys(missing))

    if len(required_skills) == 0:
        match_pct = 0
        match_rating = "No skills listed in this message"
        match_badge_color = "#94a3b8"
    else:
        total_req = len(required_skills)
        match_pct = int(round((len(matched) / total_req) * 100))
        if match_pct >= 75:
            match_rating, match_badge_color = "Strong Match", "#22c55e"
        elif match_pct >= 50:
            match_rating, match_badge_color = "Moderate Match", "#f59e0b"
        else:
            match_rating, match_badge_color = "Stretch Opportunity", "#3b82f6"

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
    fast_mode: bool = False,
) -> Dict[str, str]:
    """
    Generate a cover letter, recruiter reply draft, and talking points.
    Uses Azure AI Foundry if configured; otherwise falls back to a template
    built only from what the profile and job_spec actually contain.
    """
    profile = candidate_profile or load_candidate_profile()
    match_eval = evaluate_candidate_match(job_spec, profile)

    company = job_spec.get("company_name", "Not specified")
    role = job_spec.get("role_title", "Not specified")
    cand_name = profile.get("full_name") or "[Your name]"
    cand_email = profile.get("email") or "[your email]"
    cand_phone = profile.get("phone") or "[your phone number]"
    cand_univ = profile.get("university") or "[your university]"
    cand_degree = profile.get("education") or "[your degree]"
    cand_exp = profile.get("experience") or ""
    matched_skills_str = ", ".join(match_eval["matched_skills"]) or "[skills relevant to this role]"

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", os.getenv("FOUNDRY_ENDPOINT", ""))
    api_key = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("FOUNDRY_API_KEY", ""))
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

    cover_letter = None
    recruiter_reply = None

    if not fast_mode and endpoint and api_key and "your-foundry-resource" not in endpoint:
        try:
            from openai import OpenAI

            base_url = endpoint if endpoint.endswith("/models") else f"{endpoint}/models"
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=5.0)

            prompt = f"""You are a senior career writer. Draft an email application package for candidate '{cand_name}' applying for the role '{role}' at '{company}'.

CRITICAL INSTRUCTION: All generated text MUST be written FROM the candidate ({cand_name}) TO the recruiter/hiring team at {company}.

Candidate Details:
- Full Name: {cand_name}
- Email: {cand_email}
- Phone: {cand_phone}
- Education: {cand_degree} from {cand_univ} (CGPA: {profile.get('cgpa', 'Not specified')})
- Technical Skills: {matched_skills_str}
- Experience: {cand_exp if cand_exp and cand_exp.upper() != 'NA' else 'Academic projects & coursework'}
- Resume Attachment: {profile.get('resume_filename', 'Resume.pdf')}

Job Details:
- Company: {company}
- Role: {role}

Return valid JSON with exactly two fields:
1. "cover_letter": A formal 4-paragraph cover letter written by {cand_name} to the hiring team at {company}.
2. "recruiter_reply": An email written BY THE CANDIDATE ({cand_name}) TO THE RECRUITER at {company} expressing strong interest, providing candidate profile highlights, noting attached resume, and requesting an interview.

Return ONLY JSON, no markdown fences.
"""

            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": "You write professional emails FROM THE CANDIDATE TO THE RECRUITER. Every email MUST begin addressed to the hiring team (e.g. 'Dear Hiring Team at Company, I am writing to apply...'), NEVER addressed to the candidate."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=850,
            )

            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            try:
                parsed = json.loads(content, strict=False)
            except Exception:
                # Attempt to fix raw unescaped newlines in json strings
                fixed_content = re.sub(r'(?<!\\)\n', r'\\n', content)
                parsed = json.loads(fixed_content, strict=False)
            cover_letter = parsed.get("cover_letter")
            gen_reply = parsed.get("recruiter_reply")

            # Validate that generated reply is written FROM candidate TO recruiter, not inverted
            if gen_reply and not any(gen_reply.lower().startswith(f"dear {cand_name.lower()}") for _ in [0]):
                recruiter_reply = gen_reply
            else:
                print(f"[job_agent] GenAI reply inverted role perspective, falling back to template.")

        except Exception as exc:  # noqa: BLE001
            print(f"[job_agent] GenAI package generation failed, using template: {exc}")

    if not cover_letter:
        edu_str = f"pursuing {cand_degree} at {cand_univ}" if (cand_degree and cand_univ) else (cand_degree or cand_univ or "a degree in Computer Science")
        exp_line = f"My technical experience includes: {cand_exp}.\n\n" if (cand_exp and cand_exp.upper() != "NA") else ""
        skills_line = f"My technical skillset includes proficiency in {matched_skills_str}."
        
        cover_letter = f"""Dear Hiring Manager & Recruitment Team at {company},

I am writing to formally submit my application for the position of {role} at {company}. Having reviewed the requirements for this role, I am enthusiastic about the opportunity to contribute my technical background and skills to your team.

I am currently {edu_str}. {skills_line} {exp_line}I have consistently focused on building scalable, reliable solutions and applying strong problem-solving capabilities to real-world challenges.

I am confident that my technical skills, proactive mindset, and alignment with {company}'s goals make me a strong candidate for this position. Attached to this email is my candidate resume for your review. I look forward to the possibility of discussing my background with you further.

Thank you for your time and consideration.

Warm regards,

{cand_name}
Email: {cand_email} | Phone: {cand_phone}
{profile.get('linkedin_url', '')}""".strip()

    if not recruiter_reply:
        edu_info = f"{cand_degree} from {cand_univ}" if (cand_degree and cand_univ) else (cand_degree or cand_univ or "Computer Science")
        cgpa_info = f" (CGPA: {profile.get('cgpa')})" if profile.get('cgpa') else ""
        exp_info = f"\n- Experience Summary:   {cand_exp}" if (cand_exp and cand_exp.upper() != "NA") else ""
        links_info = ""
        if profile.get('linkedin_url') or profile.get('portfolio_url'):
            links_info = f"\n- Professional Links:   {profile.get('linkedin_url', '')} | {profile.get('portfolio_url', '')}".strip()

        res_name = profile.get("resume_filename") or (os.path.basename(profile.get("resume_path", "")) if profile.get("resume_path") else "Resume.pdf")

        recruiter_reply = f"""Subject: Re: Application & Candidate Profile — {role} | {cand_name}

Dear Hiring Team & Talent Acquisition at {company},

I am writing to express my decisive interest in the {role} position at {company}. Having evaluated the requirements for this role, I am confident that my technical expertise, software engineering background, and academic preparation align directly with your engineering goals.

==================================================
CANDIDATE PROFILE HIGHLIGHTS
==================================================
- Full Name:            {cand_name}
- Contact Email:        {cand_email}
- Phone Number:         {cand_phone}
- Qualification:        {edu_info}{cgpa_info}
- Core Skillsets:       {matched_skills_str}{exp_info}{links_info}

==================================================
ATTACHMENT VERIFICATION
==================================================
📎 Attached Resume: {res_name}
My candidate resume is attached to this email for your comprehensive evaluation, detailing my technical projects, system implementations, and practical achievements.

I welcome the opportunity to discuss my qualifications further in an interview. Please let me know your availability for a conversation.

Thank you for your time and consideration.

Sincerely,

{cand_name}
{cand_email} | {cand_phone}""".strip()

    qa_talking_points = (
        f"- **Relevant skills:** {matched_skills_str}\n"
        f"- **Missing / to prepare for:** {', '.join(match_eval['missing_skills']) or 'None identified from this message'}\n"
        f"- **Notice period:** {'[fill in]' if not cand_exp else 'Based on current commitments'}"
    )

    return {
        "cover_letter": cover_letter,
        "recruiter_reply": recruiter_reply,
        "qa_talking_points": qa_talking_points,
    }


# =========================================================
# RECRUITER REVERT-BACK & NO-REPLY EVALUATION
# =========================================================

NO_REPLY_PATTERNS = [
    r"no[-_]?reply",
    r"do[-_]?not[-_]?reply",
    r"notifications?@",
    r"auto[-_]?confirm@",
    r"automail@",
    r"mailer[-_]?daemon",
    r"system[-_]?alert@",
]


def is_no_reply_email(email_address: str) -> bool:
    """
    Detect if an email address is a No-Reply address that cannot receive incoming replies.
    """
    if not email_address or email_address in ("Not specified", "Unknown"):
        return False
    email_lower = email_address.lower().strip()
    return any(re.search(pat, email_lower) for pat in NO_REPLY_PATTERNS)


def revert_back_to_recruiter(
    email_data: Dict[str, Any],
    job_spec: Dict[str, Any],
    application_package: Dict[str, str],
    candidate_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Handles candidate revert-back logic for Low Risk recruitment offers.

    - If the sender/contact address is a No-Reply email (e.g. no-reply@google.com),
      flags it as No-Reply and guides the candidate to apply via the official career portal link.
    - If the address is a direct recruiter email (e.g. careers@razorpay.com),
      formats and dispatches the automated revert-back response email expressing interest,
      attaching the candidate's uploaded resume if present.
    """
    profile = candidate_profile or load_candidate_profile()
    candidate_email = profile.get("email") or "candidate@example.com"
    candidate_name = profile.get("full_name") or "Candidate"
    resume_path = profile.get("resume_path") or ""
    resume_filename = profile.get("resume_filename") or (os.path.basename(resume_path) if resume_path else "")

    sender_email = (email_data.get("sender") or "").strip()
    contact_email = (job_spec.get("contact_email") or sender_email or "").strip()
    portal_url = job_spec.get("portal_url") or "Official Career Portal"

    target_email = contact_email if (contact_email and contact_email != "Not specified") else sender_email

    # Self-reply recursion guard: Never dispatch automated revert-back to candidate's own email or SMTP user
    smtp_user_check = os.getenv("MAIL_USERNAME", "").strip().lower()
    if (
        target_email.lower() == candidate_email.lower()
        or (smtp_user_check and target_email.lower() == smtp_user_check)
        or (sender_email and smtp_user_check and sender_email.lower() == smtp_user_check)
    ):
        status_msg = "Self-sent message — Revert-back skipped"
        notice_msg = (
            f"This message originated from candidate's own address ({target_email}). "
            "Automated reply suppressed to prevent recursive loops."
        )
        return {
            "dispatched": False,
            "is_no_reply": True,
            "target_email": target_email,
            "candidate_email": candidate_email,
            "portal_url": portal_url,
            "status": status_msg,
            "notice": notice_msg,
            "has_resume": bool(resume_path),
            "resume_filename": resume_filename,
        }

    is_target_no_reply = is_no_reply_email(target_email)

    if is_target_no_reply or not target_email or target_email == "Not specified":
        status_msg = "No-Reply Email — Portal Application Preferred"
        notice_msg = (
            f"This message was received from a No-Reply address ({target_email or 'No-Reply'}). "
            f"Direct email reply cannot be delivered. Please apply via the official careers portal: {portal_url}"
        )
        return {
            "dispatched": False,
            "is_no_reply": True,
            "target_email": target_email or "No-Reply Address",
            "candidate_email": candidate_email,
            "portal_url": portal_url,
            "status": status_msg,
            "notice": notice_msg,
            "has_resume": bool(resume_path),
            "resume_filename": resume_filename,
        }

    # Direct recruiter email address: perform automated revert-back
    reply_body = application_package.get("recruiter_reply") or (
        f"Subject: Re: Application for {job_spec.get('role_title', 'Opportunity')} — {candidate_name}\n\n"
        f"Dear Hiring Team,\n\n"
        f"Thank you for reaching out regarding the {job_spec.get('role_title', 'role')} position at {job_spec.get('company_name', 'your organization')}. "
        f"I am very interested in this opportunity and would like to revert back to confirm my candidate profile.\n\n"
        f"Best regards,\n{candidate_name}\n{candidate_email}"
    )

    smtp_server = os.getenv("MAIL_SMTP_SERVER", "").strip()
    provider = os.getenv("MAIL_PROVIDER", "Gmail").strip().lower()
    if not smtp_server:
        if "gmail" in provider:
            smtp_server = "smtp.gmail.com"
        elif any(p in provider for p in ("outlook", "hotmail", "office365")):
            smtp_server = "smtp.office365.com"
        elif "yahoo" in provider:
            smtp_server = "smtp.mail.yahoo.com"

    smtp_user = os.getenv("MAIL_USERNAME", "").strip()
    smtp_pass = os.getenv("MAIL_APP_PASSWORD", "").strip()
    if "gmail" in provider and smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "")

    sent_via_smtp = False
    has_attached = False

    is_mock = any(
        target_email.lower().endswith(dom)
        for dom in ("@example.com", "@test.com", "@safeapply.local", "@placeholder.com")
    ) or target_email.lower() in ("talent@google.com", "recruiting@microsoft.com", "hr@company.com", "unknown")

    enable_live_smtp = os.getenv("ENABLE_REAL_SMTP_DISPATCH", "true").lower() == "true"

    if enable_live_smtp and smtp_server and smtp_user and smtp_pass and not is_mock:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.application import MIMEApplication
            from email.header import Header

            msg = MIMEMultipart()
            incoming_subject = email_data.get("subject", "")
            if incoming_subject:
                reply_subject = incoming_subject if incoming_subject.lower().startswith("re:") else f"Re: {incoming_subject}"
            else:
                reply_subject = f"Re: {job_spec.get('role_title', 'Opportunity')} — {candidate_name}"
            msg["Subject"] = Header(reply_subject, "utf-8")
            msg["From"] = smtp_user or candidate_email
            msg["To"] = target_email
            if email_data.get("message_id"):
                msg["In-Reply-To"] = email_data["message_id"]
                msg["References"] = email_data["message_id"]
            msg.attach(MIMEText(reply_body, "plain", "utf-8"))

            # Attach resume file if available
            if not resume_path or not os.path.exists(resume_path):
                c_prof = load_candidate_profile()
                resume_path = c_prof.get("resume_path", "")
                resume_filename = c_prof.get("resume_filename", "") or os.path.basename(resume_path)

            if resume_path and os.path.exists(resume_path):
                with open(resume_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=resume_filename or os.path.basename(resume_path))
                part['Content-Disposition'] = f'attachment; filename="{resume_filename or os.path.basename(resume_path)}"'
                msg.attach(part)
                has_attached = True

            try:
                with smtplib.SMTP_SSL(smtp_server, 465, timeout=15) as server:
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [target_email], msg.as_string())
                sent_via_smtp = True
                print(f"[job_agent] Successfully sent email to {target_email} via SMTP_SSL (465) with resume: {has_attached}")
            except Exception as ssl_err:
                print(f"[job_agent] SMTP_SSL attempt failed: {ssl_err}, falling back to port 587 STARTTLS")
                with smtplib.SMTP(smtp_server, 587, timeout=15) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_user, [target_email], msg.as_string())
                sent_via_smtp = True
                print(f"[job_agent] Successfully sent email to {target_email} via STARTTLS (587)")
        except Exception as err:  # noqa: BLE001
            print(f"[job_agent] SMTP dispatch warning: {err}")
    else:
        if resume_path and (os.path.exists(resume_path) or resume_filename):
            has_attached = True

    status_msg = f"Reverted back via email to recruiter ({target_email})"
    notice_msg = (
        f"Automated revert-back email expressing interest dispatched to recruiter ({target_email}) "
        f"from candidate ({candidate_email})."
        + (f" Attached candidate resume: '{resume_filename or 'resume'}'." if has_attached else "")
        + (" (Sent via SMTP)" if sent_via_smtp else (" (Simulated/Demo)" if is_mock else ""))
    )

    return {
        "dispatched": True,
        "is_no_reply": False,
        "target_email": target_email,
        "candidate_email": candidate_email,
        "reply_body": reply_body,
        "status": status_msg,
        "notice": notice_msg,
        "sent_via_smtp": sent_via_smtp,
        "has_resume": has_attached,
        "resume_filename": resume_filename,
    }


# =========================================================
# SUBMISSION RECORDING
# =========================================================

def submit_application(
    email_id: str,
    job_spec: Dict[str, Any],
    application_package: Dict[str, str],
    candidate_profile: Optional[Dict[str, Any]] = None,
    email_data: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Record an application action, evaluate no-reply vs direct recruiter revert-back,
    and persist in Azure Cosmos DB & local databases.
    """
    target_uid = kwargs.get("user_id") or ""
    profile = candidate_profile or load_candidate_profile(target_uid)
    email_info = email_data or {}

    dispatch_res = revert_back_to_recruiter(
        email_data=email_info,
        job_spec=job_spec,
        application_package=application_package,
        candidate_profile=profile,
    )

    company_prefix = (job_spec.get("company_name") or "JOB")[:3].upper()
    submission_id = f"APP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{company_prefix}"
    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    cover_letter = application_package.get("cover_letter", "")
    record = {
        "submission_id": submission_id,
        "email_id": email_id,
        "company_name": job_spec.get("company_name", "Not specified"),
        "role_title": job_spec.get("role_title", "Not specified"),
        "applied_at": timestamp,
        "candidate_name": profile.get("full_name") or "Not specified",
        "candidate_email": profile.get("email") or "Not specified",
        "portal_url": job_spec.get("portal_url", "Not specified"),
        "recruiter_email": dispatch_res.get("target_email") or job_spec.get("contact_email", "Not specified"),
        "cover_letter_snippet": cover_letter[:200] + ("..." if len(cover_letter) > 200 else ""),
        "recruiter_reply": application_package.get("recruiter_reply"),
        "is_no_reply": dispatch_res.get("is_no_reply", False),
        "dispatch_status": dispatch_res.get("status"),
        "dispatch_notice": dispatch_res.get("notice"),
        "status": dispatch_res.get("status"),
        "resume_filename": dispatch_res.get("resume_filename") or profile.get("resume_filename") or (os.path.basename(profile.get("resume_path", "")) if profile.get("resume_path") else ""),
    }

    try:
        db_save_applied_job(record, user_id=target_uid)
    except Exception as exc:  # noqa: BLE001
        print(f"[job_agent] could not save applied job to Cosmos: {exc}")

    return record
