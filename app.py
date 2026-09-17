"""
SafeApply — AI Recruitment Scam Detector
Interactive Web Application built with Streamlit
Demonstrating GenAI, RAG, Agent Orchestration, Tool Use, and Responsible AI.
"""

import time
import streamlit as st

from agent import (
    analyze_job_offer,
    is_azure_openai_configured,
    is_github_models_configured,
)
from extractor import is_azure_language_configured
from search_indexer import is_azure_configured as is_azure_search_configured


# ----------------- PAGE CONFIGURATION -----------------
st.set_page_config(
    page_title="SafeApply — AI Recruitment Scam Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------- STYLING -----------------
st.markdown(
    """
    <style>
        .main-title {
            font-size: 1.9rem;
            font-weight: 700;
            color: var(--text-color);
            margin-bottom: 0.15rem;
        }

        .sub-title {
            font-size: 0.95rem;
            color: var(--text-color);
            opacity: 0.65;
            margin-bottom: 1.6rem;
            max-width: 720px;
        }

        .risk-badge {
            display: inline-block;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 0.25rem 0.85rem;
            border-radius: 6px;
            letter-spacing: 0.02em;
        }

        .badge-high { background-color: rgba(239, 68, 68, 0.16); color: #ef4444; }
        .badge-medium { background-color: rgba(245, 158, 11, 0.16); color: #f59e0b; }
        .badge-low { background-color: rgba(34, 197, 94, 0.16); color: #22c55e; }

        .section-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--text-color);
            opacity: 0.55;
            margin-bottom: 0.4rem;
        }

        .attr-row {
            font-size: 0.92rem;
            color: var(--text-color);
            opacity: 0.85;
            padding: 0.15rem 0;
        }

        .attr-row b { opacity: 1; }

        .disclaimer-box {
            border-left: 3px solid rgba(148, 163, 184, 0.7);
            background-color: rgba(148, 163, 184, 0.08);
            padding: 0.85rem 1rem;
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--text-color);
            opacity: 0.85;
            margin-top: 1.2rem;
        }

        .status-line {
            font-size: 0.85rem;
            color: var(--text-color);
            opacity: 0.85;
            padding: 0.1rem 0;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------- PRESET SAMPLES -----------------
PRESET_SAMPLES = {
    "Select a preset sample or paste custom text...": "",

    "🚨 High Risk Scam (Advance Fee & Fake Domain)": (
        "Congratulations! You have been selected at TechCorp Solutions for the role of Graduate Software Engineer.\n"
        "Annual package: INR 8,00,000 per annum.\n"
        "To confirm your placement slot and receive your formal appointment letter, please remit a refundable registration fee "
        "of Rs 1,499 via UPI within 2 hours.\n"
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


# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 🛡️ SafeApply")
    st.caption("Cloud service status")

    if is_azure_openai_configured():
        foundry_status = "🟢 Active — Azure AI Foundry"
    elif is_github_models_configured():
        foundry_status = "🟢 Active — GitHub Models"
    else:
        foundry_status = "🟡 Local mode"

    search_status = "🟢 Active" if is_azure_search_configured() else "🟡 Local RAG"
    lang_status = "🟢 Active" if is_azure_language_configured() else "🟡 Regex heuristics"

    st.markdown(
        f"<div class='status-line'><b>GenAI</b> — {foundry_status}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='status-line'><b>Search / RAG</b> — {search_status}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='status-line'><b>Language</b> — {lang_status}</div>",
        unsafe_allow_html=True,
    )

    st.divider()
    st.caption("AI-103 concepts demonstrated")
    st.markdown(
        "- GenAI grounded explanation\n"
        "- Evidence-grounded RAG retrieval\n"
        "- Agent orchestration\n"
        "- Domain & salary tool use\n"
        "- Responsible AI guardrails"
    )

    st.divider()
    st.caption("v1.0.0 · SafeApply Recruitment Scam Detector")


# ----------------- MAIN HEADER -----------------
st.markdown('<div class="main-title">🛡️ SafeApply</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="sub-title">'
    "An AI agent that reads a job offer, checks it against known scam patterns, "
    "verifies the domain and salary, and gives a plain-English risk read — advisory, not a verdict."
    "</div>",
    unsafe_allow_html=True,
)


# ----------------- INPUT SECTION -----------------
selected_preset = st.selectbox(
    "Try a sample, or paste your own offer below",
    options=list(PRESET_SAMPLES.keys()),
    index=0,
    label_visibility="visible",
)

default_text = (
    PRESET_SAMPLES[selected_preset]
    if selected_preset != "Select a preset sample or paste custom text..."
    else ""
)

offer_input = st.text_area(
    "Job offer text",
    value=default_text,
    height=170,
    placeholder="Paste the email, WhatsApp message, or placement letter text here...",
    label_visibility="collapsed",
)

analyze_button = st.button(
    "🔍 Analyze Offer",
    type="primary",
    use_container_width=False,
)


# ----------------- ANALYSIS RESULTS -----------------
if analyze_button:
    if not offer_input or len(offer_input.strip()) < 15:
        st.warning("Please enter or select a valid job offer text to analyze.")

    else:
        with st.spinner("Running extraction, RAG retrieval, and synthesis..."):
            start_time = time.time()
            result = analyze_job_offer(offer_input)
            latency = time.time() - start_time

        risk_level = result["risk_level"]
        risk_score = result["risk_score"]

        badge_map = {
            "High": ("badge-high", "High risk"),
            "Medium": ("badge-medium", "Medium risk"),
            "Low": ("badge-low", "Low risk"),
        }

        badge_class, badge_label = badge_map.get(
            risk_level,
            ("badge-medium", risk_level),
        )

        st.divider()

        with st.container(border=True):
            top = st.columns([3, 1])

            with top[0]:
                st.markdown(
                    f'<span class="risk-badge {badge_class}">{badge_label}</span>',
                    unsafe_allow_html=True,
                )
                st.write(result["explanation"])

            with top[1]:
                st.metric("Risk score", f"{risk_score}/100")

            st.caption(
                f"Processed in {latency:.2f}s · {result['execution_mode']}"
            )

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                '<div class="section-label">Extracted attributes</div>',
                unsafe_allow_html=True,
            )

            with st.container(border=True):
                extracted = result.get("extracted_data", {})

                st.markdown(
                    f"<div class='attr-row'><b>Company</b> — {extracted.get('company_name', 'Not specified')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='attr-row'><b>Salary</b> — {extracted.get('salary', 'Not specified')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='attr-row'><b>Email</b> — {extracted.get('contact_email', 'Not specified')}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div class='attr-row'><b>Domain</b> — {extracted.get('contact_domain', 'Not specified')}</div>",
                    unsafe_allow_html=True,
                )

                actions = extracted.get("requested_actions", [])

                if actions:
                    st.markdown(
                        "<div class='attr-row' style='margin-top:0.4rem;'><b>Requested actions</b></div>",
                        unsafe_allow_html=True,
                    )
                    for act in actions:
                        st.markdown(
                            f"<div class='attr-row'>· {act}</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div class='attr-row' style='margin-top:0.4rem;'><b>Requested actions</b> — none flagged</div>",
                        unsafe_allow_html=True,
                    )

        with col2:
            st.markdown(
                '<div class="section-label">Flagged indicators</div>',
                unsafe_allow_html=True,
            )

            with st.container(border=True):
                flags = result.get("identified_red_flags", [])

                no_flag_messages = {
                    "No scam red flags detected.",
                    "No strong scam red flags detected by the current checks.",
                }

                if flags and not (
                    len(flags) == 1 and flags[0] in no_flag_messages
                ):
                    for flag in flags:
                        st.markdown(
                            f"<div class='attr-row'>🚩 {flag}</div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        "<div class='attr-row'>No strong red flags identified by the current checks.</div>",
                        unsafe_allow_html=True,
                    )

        st.write("")
        st.markdown(
            '<div class="section-label">Agent tool outputs</div>',
            unsafe_allow_html=True,
        )

        tool_tabs = st.tabs(
            [
                "RAG red-flag checker",
                "Domain verification",
                "Salary sanity check",
            ]
        )

        with tool_tabs[0]:
            rag_matches = result["tool_outputs"].get("rag_matches", [])

            if rag_matches:
                st.caption(
                    f"{len(rag_matches)} grounded pattern reference(s) "
                    "retrieved from the scam-pattern knowledge base"
                )

                for match in rag_matches:
                    with st.container(border=True):
                        st.markdown(
                            f"**{match.get('category', 'Unknown')}** "
                            f"&nbsp;·&nbsp; Search Score `{match.get('score', 0)}`"
                        )

                        st.markdown("**Retrieved Pattern**")
                        st.caption(
                            match.get(
                                "pattern",
                                "No reference pattern available.",
                            )
                        )

                        evidence = match.get("evidence", [])

                        if evidence:
                            st.markdown("**Observed Evidence in This Offer**")

                            for item in evidence:
                                st.caption(f"• {item}")
                        else:
                            st.caption(
                                "No directly grounded evidence was attached to this reference."
                            )

            else:
                st.caption(
                    "No grounded scam-pattern references were identified in the knowledge base."
                )

        with tool_tabs[1]:
            d_check = result["tool_outputs"].get("domain_verification", {})

            st.markdown(f"**Status** — {d_check.get('status', 'N/A')}")
            st.markdown(f"**Severity** — {d_check.get('severity', 'LOW')}")
            st.caption(d_check.get("message", ""))

        with tool_tabs[2]:
            s_check = result["tool_outputs"].get("salary_sanity", {})

            st.markdown(
                f"**Flagged** — {s_check.get('is_flagged', False)}"
            )
            st.markdown(
                f"**Claimed compensation** — {s_check.get('claimed_salary', 'N/A')}"
            )
            st.caption(s_check.get("message", ""))

        st.markdown(
            f"""
            <div class="disclaimer-box">
                <b>Responsible AI notice</b> —
                {result['responsible_ai_disclaimer']}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ----------------- EMPTY / LANDING STATE -----------------
else:
    st.info(
        "Pick a sample above and click **Analyze Offer** to see it in action."
    )

    st.write("")
    f1, f2, f3 = st.columns(3)

    with f1:
        with st.container(border=True):
            st.markdown("**RAG knowledge base**")
            st.caption(
                "Cross-references offer evidence against curated recruitment-fraud patterns via Azure AI Search."
            )

    with f2:
        with st.container(border=True):
            st.markdown("**Agent orchestration**")
            st.caption(
                "Coordinates extraction, domain verification, salary analysis, deterministic scoring, and GenAI explanation."
            )

    with f3:
        with st.container(border=True):
            st.markdown("**Responsible AI**")
            st.caption(
                "Advisory-only phrasing with evidence grounding and false-positive resistance."
            )

