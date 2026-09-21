"""
SafeApply — Autonomous Recruitment Security & Job Application Agent

A unified, agentic platform combining:
1. Recruitment Mailbox Ingestion & Autonomous Inbox Scanner
2. 4-Pillar Multi-Modal Risk Analysis (Rules + EMSCAD ML + Azure AI Search RAG + Azure AI Foundry)
3. Threat Quarantine Vault & Tamper-Evident Audit Logging
4. Autonomous Job Application Agent (Profile Skill Matching, Tailored Cover Letters & Recruiter Drafts)
5. Ad-Hoc Text Analyzer & Candidate Profile Configuration
"""

import os
import json
import time
import sys
import importlib
import streamlit as st

st.set_page_config(
    page_title="SafeApply — Recruitment Security & Job Agent",
    page_icon="🛡️",
    layout="wide",
)

import ui_mailbox
importlib.reload(ui_mailbox)
from ui_mailbox import render_inbox_view, render_spam_view, render_sidebar_status
from background_sync import start_background_sync

# Automatically run background email fetcher daemon without requiring manual clicks
start_background_sync()
from agent import (
    analyze_job_offer,
    is_azure_openai_configured,
    is_github_models_configured,
)
from extractor import is_azure_language_configured
from search_indexer import is_azure_configured as is_azure_search_configured
# from mail_agent import (
#     MailboxManager,
#     DEFAULT_DEMO_EMAILS,
#     fetch_live_emails,
#     parse_eml_content,
# )
# from security_actions import (
#     quarantine_email,
#     restore_email_from_vault,
#     get_quarantined_records,
#     generate_verification_checklist,
# )
from job_agent import (
    extract_job_spec,
    evaluate_candidate_match,
    generate_application_package,
    submit_application,
    load_candidate_profile,
    save_candidate_profile,
    load_applied_jobs,
)

try:
    from job_agent import is_candidate_profile_complete
except ImportError:
    def is_candidate_profile_complete(profile):
        if not profile:
            return False
        fn = (profile.get("full_name") or "").strip()
        em = (profile.get("email") or "").strip()
        rp = (profile.get("resume_path") or "").strip()
        rf = (profile.get("resume_filename") or "").strip()
        return bool(fn and em and (rp or rf))


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="SafeApply — Autonomous Recruitment Security & Job Application Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# PREMIUM STYLING
# =========================================================

st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.1rem;
            font-weight: 800;
            color: var(--text-color);
            margin-bottom: 0.15rem;
            letter-spacing: -0.02em;
        }
        .sub-title {
            font-size: 1.0rem;
            color: var(--text-color);
            opacity: 0.75;
            margin-bottom: 1.5rem;
            max-width: 900px;
            line-height: 1.5;
        }
        .risk-badge {
            display: inline-block;
            font-size: 0.9rem;
            font-weight: 700;
            padding: 0.3rem 0.9rem;
            border-radius: 6px;
            letter-spacing: 0.03em;
        }
        .badge-critical {
            background-color: rgba(220, 38, 38, 0.2);
            color: #dc2626;
            border: 1px solid rgba(220, 38, 38, 0.4);
        }
        .badge-high {
            background-color: rgba(239, 68, 68, 0.18);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.35);
        }
        .badge-medium {
            background-color: rgba(245, 158, 11, 0.18);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.35);
        }
        .badge-low {
            background-color: rgba(34, 197, 94, 0.18);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.35);
        }
        .badge-neutral {
            background-color: rgba(148, 163, 184, 0.18);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.35);
        }
        .pill-matched {
            display: inline-block;
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.82rem;
            font-weight: 600;
            margin: 0.15rem;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .pill-missing {
            display: inline-block;
            background: rgba(148, 163, 184, 0.12);
            color: #94a3b8;
            padding: 0.2rem 0.6rem;
            border-radius: 12px;
            font-size: 0.82rem;
            font-weight: 500;
            margin: 0.15rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
        }
        .email-card {
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 8px;
            padding: 0.85rem 1.1rem;
            margin-bottom: 0.65rem;
            background-color: rgba(148, 163, 184, 0.03);
            transition: all 0.2s ease;
        }
        .email-card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            background-color: rgba(99, 102, 241, 0.04);
        }
        .section-label {
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-color);
            opacity: 0.6;
            margin-bottom: 0.4rem;
        }
        .attr-row {
            font-size: 0.92rem;
            color: var(--text-color);
            opacity: 0.88;
            padding: 0.15rem 0;
        }
        .disclaimer-box {
            border-left: 3px solid rgba(99, 102, 241, 0.7);
            background-color: rgba(99, 102, 241, 0.06);
            padding: 0.85rem 1rem;
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--text-color);
            opacity: 0.85;
            margin-top: 1.2rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.45rem;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE INITIALIZATION
# =========================================================

# if "mailbox_mgr" not in st.session_state:
#     st.session_state.mailbox_mgr = MailboxManager()

# if "selected_email_id" not in st.session_state:
#     st.session_state.selected_email_id = "EML-001"

if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = load_candidate_profile()

if "application_packages" not in st.session_state:
    st.session_state.application_packages = {}

# =========================================================
# MANDATORY CANDIDATE PROFILE ONBOARDING WINDOW
# =========================================================

profile = st.session_state.candidate_profile

if not is_candidate_profile_complete(profile):
    st.markdown('<div class="main-title">📋 Welcome to SafeApply</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">'
        "Please complete your candidate profile details and upload your resume below to activate the "
        "autonomous job application and recruiter revert-back engine."
        "</div>",
        unsafe_allow_html=True,
    )
    st.warning("⚠️ **Candidate Profile Setup Required**: You must enter your details and upload your resume before accessing the application hub.")
    
    with st.container(border=True):
        st.markdown("### 📋 Candidate Profile & Resume Onboarding")
        st.caption("Provide your details to personalize your application packages and automated recruiter revert-back responses.")
        
        with st.form("startup_onboarding_form"):
            ob_c1, ob_c2 = st.columns(2)
            with ob_c1:
                ob_name = st.text_input("Full Name *", value=profile.get("full_name", ""))
                ob_email = st.text_input("Email Address *", value=profile.get("email", ""))
                ob_phone = st.text_input("Phone Number", value=profile.get("phone", ""))
                ob_edu = st.text_input("Degree / Major", value=profile.get("education", ""))
            with ob_c2:
                ob_univ = st.text_input("University / College", value=profile.get("university", ""))
                ob_gpa = st.text_input("GPA / Percentage", value=profile.get("gpa", ""))
                ob_linkedin = st.text_input("LinkedIn Profile", value=profile.get("linkedin_url", ""))
                ob_portfolio = st.text_input("Portfolio / GitHub", value=profile.get("portfolio_url", ""))

            ob_skills = st.text_area(
                "Technical Skills (comma-separated)",
                value=", ".join(profile.get("skills", [])),
                height=70,
                placeholder="Python, REST APIs, SQL, Data Structures, Git, Docker...",
            )
            ob_exp = st.text_area(
                "Experience & Project Summary",
                value=profile.get("experience", ""),
                height=85,
                placeholder="Software Engineering Intern (6 months) - Built backend microservices...",
            )
            ob_resume = st.file_uploader(
                "Upload Candidate Resume (PDF, DOCX, TXT) *",
                type=["pdf", "docx", "txt"],
                help="This resume file will be attached to outgoing revert-back emails sent to recruiters.",
            )

            if st.form_submit_button("🚀 Save Profile & Continue to SafeApply", type="primary", use_container_width=True):
                if not ob_name.strip() or not ob_email.strip():
                    st.error("Please provide both your Full Name and Email Address.")
                elif ob_resume is None and not profile.get("resume_path") and not profile.get("resume_filename"):
                    st.error("Please upload your Resume file (PDF, DOCX, or TXT).")
                else:
                    resume_path = profile.get("resume_path", "")
                    resume_filename = profile.get("resume_filename", "")
                    if ob_resume is not None:
                        os.makedirs("uploads", exist_ok=True)
                        save_dest = os.path.join("uploads", ob_resume.name)
                        with open(save_dest, "wb") as f:
                            f.write(ob_resume.getbuffer())
                        resume_path = os.path.abspath(save_dest)
                        resume_filename = ob_resume.name
                    
                    new_profile = {
                        "full_name": ob_name.strip(),
                        "email": ob_email.strip(),
                        "phone": ob_phone.strip(),
                        "education": ob_edu.strip(),
                        "university": ob_univ.strip(),
                        "gpa": ob_gpa.strip(),
                        "linkedin_url": ob_linkedin.strip(),
                        "portfolio_url": ob_portfolio.strip(),
                        "skills": [s.strip() for s in ob_skills.split(",") if s.strip()],
                        "experience": ob_exp.strip(),
                        "resume_path": resume_path,
                        "resume_filename": resume_filename,
                    }
                    save_candidate_profile(new_profile)
                    st.session_state.candidate_profile = new_profile
                    st.success("Candidate Profile & Resume saved successfully!")
                    st.rerun()
    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("### 🛡️ SafeApply Agent")
    st.caption("Autonomous Recruitment Defense & Job Hub")

    if is_azure_openai_configured():
        foundry_status = "🟢 Active (Phi-4-mini)"
    elif is_github_models_configured():
        foundry_status = "🟢 Active (GitHub Models)"
    else:
        foundry_status = "🟡 Local Fallback Mode"

    search_status = "🟢 Active (Azure Search)" if is_azure_search_configured() else "🟡 Local RAG Patterns"
    lang_status = "🟢 Active (Azure Language)" if is_azure_language_configured() else "🟡 Regex Heuristics"

    st.markdown(f"**GenAI Layer**: {foundry_status}")
    st.markdown(f"**Knowledge RAG**: {search_status}")
    st.markdown(f"**Entity Extraction**: {lang_status}")
    st.markdown("**EMSCAD ML**: 🟢 Active (Joblib Classifier)")
    render_sidebar_status()
    st.divider()

    st.caption("Agent Capabilities")
    st.markdown(
        """
        - 📬 **Mail Ingestion & Screening**
        - 🛡️ **4-Pillar Threat Detection**
        - ️ **Add to SafeApply Quarantine**
        - 🎯 **Candidate Profile Matching**
        - ✍️ **Tailored Cover Letter Gen**
        - 🚀 **1-Click Application Workflow**
        """
    )

    st.divider()

    profile = st.session_state.candidate_profile
    st.caption("Active Candidate")
    st.markdown(f"👤 **{profile.get('full_name') or 'Not Configured'}**")
    st.caption(f"{profile.get('education') or 'No Degree Specified'}")
    st.caption(f"Skills: {', '.join(profile.get('skills', [])) if profile.get('skills') else 'None'}")

    st.divider()
    st.caption("Responsible AI: SafeApply requires human confirmation before quarantining offers or recording applications.")


# =========================================================
# HEADER
# =========================================================

st.markdown('<div class="main-title">🛡️ SafeApply</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">'
    "Autonomous recruitment security and job application assistant. "
    "SafeApply connects to recruitment inboxes, scores scam risk across our 4-pillar detection pipeline "
    "(Rules + EMSCAD ML + Azure AI Search RAG + Azure AI Foundry), automatically quarantines threats, "
    "and helps candidates review and apply for legitimate opportunities."
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# TOP NAVIGATION TABS
# =========================================================

tab_mail, tab_vault, tab_adhoc, tab_profile, tab_tracker = st.tabs([
    "📬 Recruitment Mailbox & Scanner",
    "🛡️ Threat Quarantine Vault",
    "📝 Ad-Hoc Offer Analyzer",
    "👤 Candidate Profile & Skills",
    "🚀 Application Tracker",
])


# =========================================================
# TAB 1: RECRUITMENT MAILBOX & AUTONOMOUS SCANNER
# =========================================================

# with tab_mail:
#     stats = mailbox.get_mailbox_stats()

#     # Metric Row
#     m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
#     with m_col1:
#         st.metric("Total Messages", stats["total_emails"])
#     with m_col2:
#         st.metric("Recruitment", stats["recruitment_emails"])
#     with m_col3:
#         st.metric("Unscanned", stats["unscanned"])
#     with m_col4:
#         st.metric("🚨 Scams", stats["high_risk_scams"])
#     with m_col5:
#         st.metric("✅ Legitimate", stats["low_risk_legitimate"])
#     with m_col6:
#         st.metric("🚀 Applied", stats["applied"])

#     st.write("")

#     # Action Toolbar
#     act_col0, act_col1, act_col2, act_col3, act_col4 = st.columns([2.0, 1.8, 2.4, 2.0, 1.4])
#     with act_col0:
#         if st.button("⚡ Fetch from Database", use_container_width=True, help="Instantly load pre-stored emails from database cache in milliseconds"):
#             refreshed = mailbox.fetch_from_database()
#             st.success(f"Loaded {len(refreshed)} emails instantly from database!")
#             st.rerun()

#     with act_col1:
#         if st.button("⚡ Scan All Inbox", type="primary", use_container_width=True):
#             with st.spinner("Agent scanning inbox across Rules, EMSCAD ML, Azure Search RAG, and Azure Foundry..."):
#                 prog_bar = st.progress(0)
#                 unscanned_list = [e for e in mailbox.get_recruitment_emails() if e.get("status") == "unscanned"]
#                 total = len(unscanned_list)
#                 if total == 0:
#                     st.info("All recruitment emails are already scanned!")
#                 else:
#                     for i, email in enumerate(unscanned_list):
#                         mailbox.scan_single_email(email["id"])
#                         prog_bar.progress((i + 1) / total)
#                     st.success(f"Successfully scanned {total} recruitment emails!")
#                     st.rerun()

#     with act_col2:
#         with st.popover("🔗 Sync Gmail / Outlook to DB", use_container_width=True):
#             st.markdown("#### 📬 Sync Live Mailbox to Database")
#             st.caption("Fetches recent unread/recruitment messages and pre-stores them in the database for instant access.")

#             provider = st.selectbox("Email Provider", ["Gmail", "Outlook / Hotmail", "Yahoo", "Custom Server"])
#             live_user = st.text_input("Email Address", placeholder="e.g. yourname@gmail.com")
#             live_pass = st.text_input("Password or App Password", type="password", help="For Gmail, generate a 16-character App Password.")

#             custom_srv = None
#             custom_port = 993
#             if provider == "Custom Server":
#                 custom_srv = st.text_input("IMAP Server Host", "imap.yourserver.com")
#                 custom_port = st.number_input("IMAP Port", value=993)

#             fetch_count = st.slider("Max emails to fetch", min_value=3, max_value=25, value=10)

#             if provider == "Gmail":
#                 st.info(
#                     "💡 **Gmail Setup Guide:**\n\n"
#                     "1. Visit [Google Account Security](https://myaccount.google.com/security)\n"
#                     "2. Ensure **2-Step Verification** is turned ON\n"
#                     "3. Open **App passwords** (search 'App passwords' in Google settings)\n"
#                     "4. Generate password for `SafeApply` and paste the 16-letter code here (spaces automatically removed)\n"
#                     "5. **Important:** In Gmail Settings (gear icon) > See all settings > Forwarding and POP/IMAP, ensure **Enable IMAP** is turned ON."
#                 )
#             elif provider == "Outlook / Hotmail":
#                 st.caption("Works with your Microsoft Account password or an Outlook App Password.")

#             if st.button("📥 Sync Live Inbox to Database", type="primary", use_container_width=True):
#                 if not live_user or not live_pass:
#                     st.error("Please enter both email address and password / app password.")
#                 else:
#                     with st.spinner(f"Connecting to {provider} and syncing into database store..."):
#                         try:
#                             live_fetched = fetch_live_emails(
#                                 provider=provider,
#                                 username=live_user,
#                                 password_or_app_token=live_pass,
#                                 max_emails=fetch_count,
#                                 server=custom_srv,
#                                 port=custom_port,
#                             )
#                             if not live_fetched:
#                                 st.warning("Connected successfully, but no messages were returned from INBOX.")
#                             else:
#                                 count = mailbox.ingest_live_emails(live_fetched)
#                                 st.success(f"Synced {len(live_fetched)} emails directly into database cache ({count} new added)!")
#                                 st.session_state.selected_email_id = live_fetched[0]["id"]
#                                 st.rerun()
#                         except Exception as ex:
#                             st.error(f"Connection error: {str(ex)}")

#     with act_col3:
#         with st.popover("➕ Add / Upload Email", use_container_width=True):
#             st.markdown("#### 📁 Import Email File (.eml)")
#             st.caption("Export any email from Gmail or Outlook ('Download message') and drop it here.")
#             eml_file = st.file_uploader("Choose an .eml file", type=["eml"])
#             if eml_file is not None:
#                 if st.button("Ingest Uploaded .EML File", type="primary"):
#                     parsed_eml = parse_eml_content(eml_file.read())
#                     if not parsed_eml.get("is_recruitment", False):
#                         st.warning("⚠️ This email was analyzed and determined NOT to be recruitment or job-related. It has been ignored.")
#                     else:
#                         mailbox.emails.insert(0, parsed_eml)
#                         try:
#                             from database import db_save_emails
#                             db_save_emails([parsed_eml])
#                         except Exception:
#                             pass
#                         st.session_state.selected_email_id = parsed_eml["id"]
#                         st.success(f"Uploaded recruitment email '{parsed_eml['subject'][:35]}' into inbox!")
#                         st.rerun()

#             st.divider()
#             st.markdown("#### ✍️ Or Paste Manual Message")
#             new_sender = st.text_input("Sender Email", "hr.recruiter@company.com")
#             new_name = st.text_input("Sender Name", "Talent Team")
#             new_company = st.text_input("Company Name", "Tech Solutions")
#             new_role = st.text_input("Role Title", "Software Engineer")
#             new_subj = st.text_input("Subject", "Job Opportunity - Software Engineer")
#             new_body = st.text_area("Email Body", "We are pleased to offer you a role...", height=90)
#             if st.button("Ingest Pasted Email", type="primary"):
#                 if new_body.strip():
#                     created = mailbox.add_custom_email(
#                         sender=new_sender,
#                         sender_name=new_name,
#                         subject=new_subj,
#                         body=new_body,
#                         company_name=new_company,
#                         role_title=new_role,
#                     )
#                     if not created.get("is_recruitment", False):
#                         st.warning("⚠️ The pasted message does not contain recruitment or job indicators. It has been ignored.")
#                     else:
#                         st.session_state.selected_email_id = created["id"]
#                         st.success(f"Added recruitment email {created['id']} to inbox!")
#                         st.rerun()

#     with act_col4:
#         if st.button("🔄 Reset Demo", use_container_width=True):
#             st.session_state.mailbox_mgr = MailboxManager()
#             st.session_state.selected_email_id = "EML-001"
#             st.success("Reset demo inbox.")
#             st.rerun()

#     st.divider()

#     # Split View: Left = Inbox List, Right = Selected Email Dossier
#     list_col, detail_col = st.columns([4, 6])

#     with list_col:
#         st.markdown("#### 📥 Incoming Recruitment Messages")

#         # Filter option
#         filter_opt = st.selectbox(
#             "Filter Messages",
#             ["All Recruitment", "Unscanned", "🚨 High Risk Scams", "⚠️ Ambiguous", "✅ Legitimate Jobs", "🛡️ Quarantined", "🚀 Applied"],
#             index=0,
#             label_visibility="collapsed",
#         )

#         all_rec = mailbox.get_recruitment_emails()
#         filtered_emails = []

#         for e in all_rec:
#             st_val = e.get("status")
#             rl_val = e.get("risk_level")

#             if filter_opt == "All Recruitment":
#                 filtered_emails.append(e)
#             elif filter_opt == "Unscanned" and st_val == "unscanned":
#                 filtered_emails.append(e)
#             elif filter_opt == "🚨 High Risk Scams" and rl_val in ("High", "Critical") and st_val != "quarantined":
#                 filtered_emails.append(e)
#             elif filter_opt == "⚠️ Ambiguous" and rl_val == "Medium":
#                 filtered_emails.append(e)
#             elif filter_opt == "✅ Legitimate Jobs" and rl_val == "Low":
#                 filtered_emails.append(e)
#             elif filter_opt == "🛡️ Quarantined" and st_val == "quarantined":
#                 filtered_emails.append(e)
#             elif filter_opt == "🚀 Applied" and st_val == "applied":
#                 filtered_emails.append(e)

#         if not filtered_emails:
#             st.info("No emails match the selected filter.")

#         for em in filtered_emails:
#             em_id = em["id"]
#             em_status = em.get("status", "unscanned")
#             em_level = em.get("risk_level")
#             em_score = em.get("risk_score")

#             # Determine badge
#             if em_status == "quarantined":
#                 badge_html = '<span class="risk-badge badge-critical">🛡️ Quarantined</span>'
#             elif em_status == "applied":
#                 badge_html = '<span class="risk-badge badge-low">🚀 Applied</span>'
#             elif em_status == "unscanned":
#                 badge_html = '<span class="risk-badge badge-neutral">⚪ Unscanned</span>'
#             elif em_level in ("High", "Critical"):
#                 badge_html = f'<span class="risk-badge badge-high">🚨 High Risk ({em_score})</span>'
#             elif em_level == "Medium":
#                 badge_html = f'<span class="risk-badge badge-medium">⚠️ Medium Risk ({em_score})</span>'
#             else:
#                 badge_html = f'<span class="risk-badge badge-low">✅ Low Risk ({em_score})</span>'

#             # Selection highlighting
#             is_sel = (em_id == st.session_state.selected_email_id)
#             card_border = "border: 2px solid #6366f1;" if is_sel else "border: 1px solid rgba(148, 163, 184, 0.2);"

#             with st.container():
#                 st.markdown(
#                     f"""
#                     <div style="border-radius: 8px; padding: 0.75rem 0.95rem; margin-bottom: 0.45rem; background-color: rgba(148, 163, 184, 0.04); {card_border}">
#                         <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
#                             <span style="font-size: 0.8rem; font-weight: 600; opacity: 0.65;">{em['id']} · {em['date']}</span>
#                             {badge_html}
#                         </div>
#                         <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.2rem; color: var(--text-color);">{em['subject'][:55]}...</div>
#                         <div style="font-size: 0.85rem; opacity: 0.85;"><b>{em.get('company_name', 'Company')}</b> · {em.get('role_title', 'Role')}</div>
#                     </div>
#                     """,
#                     unsafe_allow_html=True,
#                 )
#                 if st.button(f"Inspect {em_id}", key=f"sel_{em_id}", use_container_width=True):
#                     st.session_state.selected_email_id = em_id
#                     st.rerun()

#     # RIGHT: Selected Email Detail & Autonomous Dossier
#     with detail_col:
#         sel_email = mailbox.get_email_by_id(st.session_state.selected_email_id)
#         if not sel_email:
#             st.info("Select an email from the left pane to view.")
#         else:
#             st.markdown(f"### 📋 Email Dossier: {sel_email['id']}")

#             with st.container(border=True):
#                 c_top1, c_top2 = st.columns([3, 1])
#                 with c_top1:
#                     st.markdown(f"**Subject:** {sel_email['subject']}")
#                     st.markdown(f"**From:** {sel_email['sender_name']} `<{sel_email['sender']}>`")
#                     st.caption(f"**Date:** {sel_email['date']} | **Claimed Employer:** {sel_email.get('company_name', 'Unknown')}")
#                 with c_top2:
#                     st_val = sel_email.get("status")
#                     if st_val == "unscanned":
#                         st.markdown('<span class="risk-badge badge-neutral">⚪ Unscanned</span>', unsafe_allow_html=True)
#                     elif st_val == "quarantined":
#                         st.markdown('<span class="risk-badge badge-critical">🛡️ Quarantined</span>', unsafe_allow_html=True)
#                     elif st_val == "applied":
#                         st.markdown('<span class="risk-badge badge-low">🚀 Applied</span>', unsafe_allow_html=True)
#                     else:
#                         rl = sel_email.get("risk_level", "Medium")
#                         sc = sel_email.get("risk_score", 50)
#                         cls_name = "badge-high" if rl in ("High", "Critical") else ("badge-medium" if rl == "Medium" else "badge-low")
#                         st.markdown(f'<span class="risk-badge {cls_name}">{rl} Risk ({sc}/100)</span>', unsafe_allow_html=True)

#             # Expandable Raw Message
#             with st.expander("📄 View Full Email Content", expanded=(sel_email.get("status") == "unscanned")):
#                 st.text(sel_email.get("body", ""))

#             # If Unscanned: Button to Scan
#             if sel_email.get("status") == "unscanned":
#                 st.write("")
#                 if st.button("🔍 Scan Email with SafeApply Agent", type="primary", use_container_width=True):
#                     with st.spinner("Evaluating with Rules + EMSCAD ML + Azure Search RAG + Azure AI Foundry..."):
#                         mailbox.scan_single_email(sel_email["id"])
#                         st.rerun()

#             # If Scanned: Present Full Multi-Pillar Analysis + Workflow Actions
#             elif sel_email.get("analysis"):
#                 analysis = sel_email["analysis"]
#                 risk_level = sel_email.get("risk_level", "Medium")
#                 risk_score = sel_email.get("risk_score", 50)

#                 st.write("")
#                 st.markdown("#### 🛡️ SafeApply Security Analysis")

#                 # Grounded AI Explanation
#                 with st.container(border=True):
#                     st.markdown(f"**Agent Risk Assessment ({risk_score}/100 — {risk_level} Risk)**")
#                     st.write(analysis.get("explanation", ""))
#                     st.caption(f"Execution Mode: {analysis.get('execution_mode', 'Live Pipeline')}")

#                 # 4-Pillar Tabs Breakdown
#                 p_tab1, p_tab2, p_tab3, p_tab4 = st.tabs([
#                     "🔍 Rules Signals",
#                     "🧠 EMSCAD ML",
#                     "📚 Azure Search RAG",
#                     "🌐 Domain & Salary",
#                 ])

#                 with p_tab1:
#                     red_flags = analysis.get("red_flags", [])
#                     if red_flags:
#                         st.error(f"**Observed Red Flags ({len(red_flags)}):**")
#                         for rf in red_flags:
#                             st.markdown(f"- 🚩 {rf}")
#                     else:
#                         st.success("✅ No direct red flags or advance fee requests observed.")

#                 with p_tab2:
#                     ml_data = analysis.get("ml_classifier", {})
#                     m_c1, m_c2 = st.columns(2)
#                     with m_c1:
#                         st.metric("Fraud Probability", f"{ml_data.get('fraud_probability_pct', 0.0):.1f}%")
#                     with m_c2:
#                         st.metric("ML Risk Band", ml_data.get("risk_band", "N/A"))

#                     top_tokens = ml_data.get("top_risk_tokens", [])
#                     if top_tokens:
#                         st.markdown("**Learned Risk Tokens:** " + ", ".join([f"`{t}`" for t in top_tokens]))
#                     st.caption("Advisory statistical signal trained on 17,880 EMSCAD job advertisements.")

#                 with p_tab3:
#                     rag_data = analysis.get("rag_scam_patterns", [])
#                     if rag_data:
#                         st.markdown(f"**Gated RAG Matches ({len(rag_data)}):**")
#                         for pat in rag_data:
#                             with st.container():
#                                 st.markdown(f"**Category:** `{pat.get('category')}`")
#                                 st.caption(f"Pattern Reference: {pat.get('pattern')}")
#                                 if pat.get("evidence"):
#                                     st.markdown(f"*Grounding Evidence in Email:* {', '.join(pat['evidence'])}")
#                     else:
#                         st.info("No gated scam patterns matched the observed text.")

#                 with p_tab4:
#                     d_check = analysis.get("domain_check", {})
#                     s_check = analysis.get("salary_check", {})
#                     st.markdown(f"**Domain Analysis:** {d_check.get('assessment', 'N/A')}")
#                     st.caption(f"Sender Domain: `{d_check.get('sender_domain', 'N/A')}` | Official Domain: `{d_check.get('expected_domain', 'N/A')}`")
#                     st.markdown(f"**Salary Sanity:** {s_check.get('assessment', 'N/A')}")

#                 st.divider()

#                 # =========================================================
#                 # AUTONOMOUS WORKFLOW ACTION ENGINES
#                 # =========================================================

#                 # PATH A: HIGH / CRITICAL RISK -> SAFEAPPLY QUARANTINE
#                 if risk_level in ("High", "Critical") and sel_email.get("status") != "quarantined":
#                     st.markdown("### 🚨 High Risk Alert — Security Action Required")
#                     st.warning(
#                         "SafeApply identified severe recruitment-scam indicators (e.g. upfront fee, urgency, domain impersonation). "
#                         "Do not send money, OTPs, or identity documents."
#                     )

#                     q_c1, q_c2 = st.columns([3, 1])
#                     with q_c1:
#                         quarantine_reason = st.text_input(
#                             "Quarantine Reason",
#                             value="Advance fee request / domain impersonation detected",
#                             key=f"q_reason_{sel_email['id']}",
#                         )
#                     with q_c2:
#                         st.write("")
#                         st.write("")
#                         if st.button("🛡️ Add to SafeApply Quarantine", type="primary", use_container_width=True):
#                             rec = quarantine_email(sel_email, reason=quarantine_reason)
#                             st.success(f"Quarantined! Threat logged to vault with record ID {rec['record_id']}.")
#                             st.rerun()

#                     st.caption("*(Prototype Quarantine: Isolates this threat in the SafeApply Threat Vault without altering your external mailbox provider)*")

#                 elif sel_email.get("status") == "quarantined":
#                     st.success("🛡️ This email has been added to SafeApply Quarantine. It is safely isolated in the Threat Vault.")

#                 # PATH B: LOW RISK -> JOB APPLICATION AGENT
#                 elif risk_level == "Low":
#                     st.markdown("### 🎯 Legitimate Opportunity — Autonomous Job Agent")
#                     st.success("SafeApply currently assesses this opportunity as low risk. The Job Application Agent is ready to assist your application.")

#                     job_spec = extract_job_spec(sel_email.get("body", ""), sel_email)
#                     profile = st.session_state.candidate_profile
#                     match_res = evaluate_candidate_match(job_spec, profile)

#                     # Match summary card
#                     with st.container(border=True):
#                         col_m1, col_m2 = st.columns([2, 3])
#                         with col_m1:
#                             st.metric(
#                                 "Candidate Skill Match",
#                                 f"{match_res['match_percentage']}%",
#                                 delta=match_res["match_rating"],
#                             )
#                         with col_m2:
#                             st.markdown(f"**Target Role:** {job_spec['role_title']} at **{job_spec['company_name']}**")
#                             st.markdown(f"**Location:** {job_spec['location']} | **Compensation:** {job_spec['salary']}")

#                         # Skills breakdown
#                         st.write("")
#                         st.markdown("**Matched Skills:**")
#                         pills_html = "".join([f'<span class="pill-matched">✓ {s}</span>' for s in match_res["matched_skills"]])
#                         st.markdown(pills_html or "*None direct*", unsafe_allow_html=True)

#                         if match_res["missing_skills"]:
#                             st.markdown("**Nice-to-Have / Missing Skills:**")
#                             pills_miss_html = "".join([f'<span class="pill-missing">△ {s}</span>' for s in match_res["missing_skills"]])
#                             st.markdown(pills_miss_html, unsafe_allow_html=True)

#                     # Generate Application Materials (Cover Letter & Recruiter Reply)
#                     pkg_key = f"pkg_{sel_email['id']}"
#                     if pkg_key not in st.session_state.application_packages:
#                         with st.spinner("Generating tailored cover letter and recruiter response via Azure AI Foundry..."):
#                             st.session_state.application_packages[pkg_key] = generate_application_package(job_spec, profile)

#                     app_pkg = st.session_state.application_packages[pkg_key]

#                     st.write("")
#                     st.markdown("#### 📝 AI-Generated Application Materials")

#                     pkg_tab1, pkg_tab2, pkg_tab3 = st.tabs([
#                         "📄 Tailored Cover Letter",
#                         "✉️ Recruiter Email Reply",
#                         "💡 Interview Talking Points",
#                     ])

#                     with pkg_tab1:
#                         edited_cl = st.text_area(
#                             "Cover Letter (Editable)",
#                             value=app_pkg["cover_letter"],
#                             height=200,
#                             key=f"cl_{sel_email['id']}",
#                         )

#                     with pkg_tab2:
#                         edited_reply = st.text_area(
#                             "Recruiter Reply (Editable)",
#                             value=app_pkg["recruiter_reply"],
#                             height=140,
#                             key=f"reply_{sel_email['id']}",
#                         )

#                     with pkg_tab3:
#                         st.markdown(app_pkg["qa_talking_points"])

#                     st.write("")
#                     if sel_email.get("status") == "applied":
#                         st.success("🎉 Application package recorded in candidate history.")
#                     else:
#                         if st.button("📋 Approve & Record Application Package", type="primary", use_container_width=True):
#                             sub_record = submit_application(
#                                 email_id=sel_email["id"],
#                                 job_spec=job_spec,
#                                 application_package={"cover_letter": edited_cl, "recruiter_reply": edited_reply},
#                                 candidate_profile=profile,
#                             )
#                             mailbox.update_email_status(sel_email["id"], "applied")
#                             st.success(f"Application package approved and recorded locally! Tracking ID: `{sub_record['submission_id']}`")
#                             st.caption("*(Prototype Note: Application materials recorded in local candidate history without contacting external career portals)*")
#                             st.balloons()
#                             st.rerun()

#                 # PATH C: MEDIUM RISK -> VERIFICATION AGENT CHECKLIST
#                 elif risk_level == "Medium":
#                     st.markdown("### ⚠️ Ambiguous Offer — Verification Agent Flow")
#                     st.warning(
#                         "This recruitment message has incomplete information, an unverified domain, or elevated statistical signals. "
#                         "Complete the verification steps below before engaging."
#                     )

#                     checklist = generate_verification_checklist(sel_email)
#                     all_verified = True
#                     for item in checklist:
#                         chk_val = st.checkbox(
#                             f"**{item['risk_type']}**: {item['description']}",
#                             value=False,
#                             key=f"chk_{sel_email['id']}_{item['id']}",
#                         )
#                         if not chk_val:
#                             all_verified = False

#                     st.write("")
#                     c_act1, c_act2 = st.columns(2)
#                     with c_act1:
#                         if st.button("✅ Confirm User Verification (Trusted Override)", use_container_width=True, disabled=not all_verified):
#                             # Flaw 7: Preserve original SafeApply risk assessment
#                             if "original_risk_score" not in sel_email or sel_email["original_risk_score"] is None:
#                                 sel_email["original_risk_score"] = sel_email.get("risk_score", 50)
#                                 sel_email["original_risk_level"] = sel_email.get("risk_level", "Medium")
#                             sel_email["user_override"] = "Verified by Candidate"
#                             sel_email["status"] = "verified"
#                             mailbox.update_email_status(sel_email["id"], "verified")
#                             st.success("Candidate verification confirmed! Original SafeApply risk score preserved in audit trail.")
#                             st.rerun()
#                         if not all_verified:
#                             st.caption("*(Complete all verification checks above to enable candidate override)*")

#                     with c_act2:
#                         if st.button("🛡️ Add to SafeApply Quarantine", use_container_width=True):
#                             quarantine_email(sel_email, reason="Failed user verification checks")
#                             st.warning("Quarantined!")
#                             st.rerun()
with tab_mail:
    def _handle_apply(email):
        profile = st.session_state.candidate_profile
        if not is_candidate_profile_complete(profile):
            st.warning("⚠️ **Candidate Profile Incomplete!** Please enter your Full Name, Email, and upload your Resume in the '👤 Candidate Profile & Skills' tab before applying.")
            st.session_state["profile_prompt_active"] = True
            return

        job_spec = extract_job_spec(email.get("body", ""), email)
        pkg_key = f"pkg_{email['id']}"
        if pkg_key not in st.session_state.application_packages:
            st.session_state.application_packages[pkg_key] = generate_application_package(job_spec, profile)
        app_pkg = st.session_state.application_packages[pkg_key]
        sub_rec = submit_application(
            email_id=email["id"],
            job_spec=job_spec,
            application_package={
                "cover_letter": app_pkg["cover_letter"],
                "recruiter_reply": app_pkg["recruiter_reply"],
            },
            candidate_profile=profile,
            email_data=email,
        )
        st.session_state[f"sub_rec_{email['id']}"] = sub_rec

    render_inbox_view(on_apply=_handle_apply)

# =========================================================
# TAB 2: THREAT QUARANTINE VAULT
# =========================================================

# with tab_vault:
#     st.markdown("### 🛡️ Quarantined Threat Vault")
#     st.caption("Isolated recruitment scams and tamper-evident security audit trail.")

#     vault_records = get_quarantined_records()

#     if not vault_records:
#         st.info("No threats currently quarantined in the vault.")
#     else:
#         st.markdown(f"**Total Quarantined Campaigns:** {len(vault_records)}")

#         for rec in vault_records:
#             with st.container(border=True):
#                 v_col1, v_col2 = st.columns([4, 1])
#                 with v_col1:
#                     st.markdown(f"#### 🚨 {rec.get('claimed_company', 'Unknown Employer')} — {rec.get('role_title', 'Role')}")
#                     st.markdown(f"**Sender:** `{rec.get('sender')}` | **Subject:** {rec.get('subject')}")
#                     st.caption(f"**Quarantined:** {rec.get('quarantined_at')} | **Record ID:** `{rec.get('record_id')}`")
#                     st.markdown(f"**Reason:** {rec.get('reason')}")

#                     indicators = rec.get("observed_indicators", [])
#                     if indicators:
#                         st.markdown("**Detected Threat Indicators:**")
#                         for ind in indicators:
#                             st.markdown(f"- 🚩 {ind}")

#                 with v_col2:
#                     st.metric("Threat Score", f"{rec.get('risk_score', 90)}/100")
#                     st.write("")
#                     if st.button("↩️ Restore to Inbox", key=f"rst_{rec['email_id']}", use_container_width=True):
#                         restore_email_from_vault(rec["email_id"], mailbox)
#                         st.success(f"Restored {rec['email_id']} back to active inbox.")
#                         st.rerun()

with tab_vault:
    render_spam_view()
# =========================================================
# TAB 3: AD-HOC TEXT ANALYZER
# =========================================================

with tab_adhoc:
    st.markdown("### 📝 Direct Recruitment Offer Analyzer")
    st.caption("Analyze any custom text, placement notice, or offer letter through the 4-pillar detection pipeline.")

    PRESET_SAMPLES = {
        "Select a preset sample or paste custom text...": "",
        "🚨 High Risk Scam (Advance Fee & Fake Domain)": (
            "Congratulations! You have been selected at TechCorp Solutions for the role of Graduate Software Engineer.\n"
            "Annual package: INR 8,00,000 per annum.\n"
            "To confirm your placement slot and receive your formal appointment letter, please remit a refundable registration fee of Rs 1,499 via UPI within 2 hours.\n"
            "Send your payment confirmation screenshot immediately to hr.techcorp@gmail.com or your candidature will be permanently cancelled."
        ),
        "✅ Legitimate Offer (Microsoft India Internship)": (
            "Dear Candidate,\n\n"
            "Following your technical interviews with our engineering team, we are pleased to offer you an internship at Microsoft India (R&D) Pvt. Ltd.\n\n"
            "Role: Software Engineering Intern\n"
            "Stipend: INR 50,000 per month\n"
            "Location: Hyderabad Campus\n\n"
            "Microsoft never charges any fees or security deposits at any stage of our recruitment process.\n"
            "Please review and sign your formal offer letter on the Microsoft Careers Portal: https://careers.microsoft.com.\n\n"
            "University Recruiting Team, Microsoft India\n"
            "Email: university-recruiting@microsoft.com"
        ),
        "⚠️ Ambiguous Offer (Unverified Small Agency)": (
            "Hi,\n\n"
            "I found your profile on LinkedIn for our boutique digital marketing agency, Apex Media.\n"
            "We have an open junior web designer role. Salary is around INR 25,000 per month depending on your portfolio.\n"
            "Please reply with your resume and sample links if interested.\n\n"
            "Regards,\n"
            "Karan\n"
            "Email: karan.apexmedia@gmail.com"
        ),
    }

    adhoc_preset = st.selectbox("Preset Samples", list(PRESET_SAMPLES.keys()), index=0)
    preset_body = PRESET_SAMPLES[adhoc_preset] if adhoc_preset != "Select a preset sample or paste custom text..." else ""

    adhoc_text = st.text_area(
        "Offer Text Input",
        value=preset_body,
        height=180,
        placeholder="Paste recruitment text, email, or message here...",
        label_visibility="collapsed",
    )

    if st.button("🔍 Run Full 4-Pillar Analysis", type="primary"):
        if not adhoc_text or len(adhoc_text.strip()) < 15:
            st.warning("Please enter at least 15 characters of offer text.")
        else:
            with st.spinner("Analyzing via Rules, EMSCAD ML, Azure Search RAG, and Azure Foundry..."):
                t0 = time.time()
                ad_res = analyze_job_offer(adhoc_text)
                lat = time.time() - t0

            ad_level = ad_res["risk_level"]
            ad_score = ad_res["risk_score"]
            badge_cls = "badge-high" if ad_level in ("High", "Critical") else ("badge-medium" if ad_level == "Medium" else "badge-low")

            st.divider()
            with st.container(border=True):
                r_c1, r_c2 = st.columns([3, 1])
                with r_c1:
                    st.markdown(f'<span class="risk-badge {badge_cls}">{ad_level} Risk</span>', unsafe_allow_html=True)
                    st.write(ad_res.get("explanation", ""))
                with r_c2:
                    st.metric("Risk Score", f"{ad_score}/100")
                st.caption(f"Processed in {lat:.2f}s · {ad_res.get('execution_mode')}")

            # 4 Pillar Breakdown
            st.write("")
            b_c1, b_c2 = st.columns(2)
            with b_c1:
                with st.container(border=True):
                    st.markdown("**1. Rules & Red Flags**")
                    flags = ad_res.get("red_flags", [])
                    if flags:
                        for f in flags:
                            st.markdown(f"- 🚩 {f}")
                    else:
                        st.success("No deterministic red flags.")

                with st.container(border=True):
                    st.markdown("**3. Azure AI Search RAG**")
                    pats = ad_res.get("rag_scam_patterns", [])
                    if pats:
                        for p in pats:
                            st.markdown(f"- `{p.get('category')}`: {p.get('pattern')}")
                    else:
                        st.info("No gated RAG patterns retrieved.")

            with b_c2:
                with st.container(border=True):
                    st.markdown("**2. EMSCAD Machine Learning**")
                    ml = ad_res.get("ml_classifier", {})
                    st.metric("Fraud Probability", f"{ml.get('fraud_probability_pct', 0.0):.1f}%")
                    st.caption(f"Risk Band: {ml.get('risk_band', 'N/A')}")
                    tokens = ml.get("top_risk_tokens", [])
                    if tokens:
                        st.caption("Top tokens: " + ", ".join(tokens))

                with st.container(border=True):
                    st.markdown("**4. Domain & Compensation Sanity**")
                    st.markdown(f"Domain: {ad_res.get('domain_check', {}).get('assessment', 'N/A')}")
                    st.markdown(f"Salary: {ad_res.get('salary_check', {}).get('assessment', 'N/A')}")


# =========================================================
# TAB 4: CANDIDATE PROFILE & PREFERENCES
# =========================================================

with tab_profile:
    st.markdown("### 👤 Candidate Profile & Job Preferences")
    st.caption("Configure your profile to personalize the Job Application Agent's skill matching and cover letter generation.")

    prof = st.session_state.candidate_profile

    with st.form("profile_form"):
        f_c1, f_c2 = st.columns(2)
        with f_c1:
            p_name = st.text_input("Full Name", prof.get("full_name", ""))
            p_email = st.text_input("Email", prof.get("email", ""))
            p_phone = st.text_input("Phone Number", prof.get("phone", ""))
            p_edu = st.text_input("Degree / Major", prof.get("education", ""))

        with f_c2:
            p_univ = st.text_input("University / College", prof.get("university", ""))
            p_gpa = st.text_input("GPA / Percentage", prof.get("gpa", ""))
            p_linkedin = st.text_input("LinkedIn Profile", prof.get("linkedin_url", ""))
            p_portfolio = st.text_input("Portfolio / GitHub", prof.get("portfolio_url", ""))

        p_skills = st.text_area(
            "Technical Skills (comma-separated)",
            value=", ".join(prof.get("skills", [])),
            height=70,
        )

        p_exp = st.text_area(
            "Internship & Project Experience Summary",
            value=prof.get("experience", ""),
            height=90,
        )

        st.markdown("#### 📄 Candidate Resume Attachment")
        current_resume = prof.get("resume_filename") or (os.path.basename(prof.get("resume_path", "")) if prof.get("resume_path") else "No resume uploaded yet")
        st.info(f"**Current Uploaded Resume:** `{current_resume}`")

        uploaded_resume = st.file_uploader("Upload Candidate Resume (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], help="This file will be attached to outgoing revert-back emails sent to recruiters.")

        if st.form_submit_button("💾 Save Profile & Resume", type="primary"):
            resume_path = prof.get("resume_path", "")
            resume_filename = prof.get("resume_filename", "")

            if uploaded_resume is not None:
                os.makedirs("uploads", exist_ok=True)
                save_dest = os.path.join("uploads", uploaded_resume.name)
                with open(save_dest, "wb") as f:
                    f.write(uploaded_resume.getbuffer())
                resume_path = os.path.abspath(save_dest)
                resume_filename = uploaded_resume.name

            updated_profile = {
                "full_name": p_name.strip(),
                "email": p_email.strip(),
                "phone": p_phone.strip(),
                "education": p_edu.strip(),
                "university": p_univ.strip(),
                "gpa": p_gpa.strip(),
                "linkedin_url": p_linkedin.strip(),
                "portfolio_url": p_portfolio.strip(),
                "skills": [s.strip() for s in p_skills.split(",") if s.strip()],
                "experience": p_exp.strip(),
                "resume_path": resume_path,
                "resume_filename": resume_filename,
            }
            save_candidate_profile(updated_profile)
            st.session_state.candidate_profile = updated_profile
            st.success(f"Candidate profile and resume ('{resume_filename or 'saved'}') updated successfully!")
            st.rerun()


# =========================================================
# TAB 5: APPLICATION TRACKER
# =========================================================

with tab_tracker:
    st.markdown("### 🚀 Job Application Tracker")
    st.caption("Audit log of all job applications prepared and submitted through SafeApply.")

    applied_jobs = load_applied_jobs()

    if not applied_jobs:
        st.info("No job applications submitted yet. Scan your inbox and click 'Submit Application' on low-risk job offers.")
    else:
        st.markdown(f"**Total Applications Sent:** {len(applied_jobs)}")

        for app in applied_jobs:
            with st.container(border=True):
                a_c1, a_c2 = st.columns([4, 1])
                with a_c1:
                    st.markdown(f"#### 💼 {app.get('role_title')} at **{app.get('company_name')}**")
                    st.caption(f"**Submitted At:** {app.get('applied_at')} | **Tracking ID:** `{app.get('submission_id')}`")
                    st.markdown(f"**Recipient / Recruiter:** `{app.get('recruiter_email')}` | **Application Portal:** {app.get('portal_url')}")
                    with st.expander("📄 View Submitted Cover Letter & Response"):
                        st.markdown("**Cover Letter:**")
                        st.text(app.get("cover_letter_snippet", ""))
                        st.markdown("**Recruiter Reply:**")
                        st.text(app.get("recruiter_reply", ""))
                with a_c2:
                    st.success(f"Status: {app.get('status', 'Active')}")


# =========================================================
# RESPONSIBLE AI DISCLAIMER FOOTER
# =========================================================

st.divider()
st.markdown(
    """
    <div class="disclaimer-box">
        <b>Responsible AI Disclaimer:</b> SafeApply is an AI-powered advisory assistant designed to identify common recruitment scam indicators and assist candidate workflows.
        It does not constitute legal counsel or an infallible determination of fraud.
        SafeApply enforces <b>human-in-the-loop control</b>: emails are only quarantined and applications are only submitted upon user approval.
        Always verify employers via official corporate channels and placement cells before sharing sensitive documents or funds.
    </div>
    """,
    unsafe_allow_html=True,
)