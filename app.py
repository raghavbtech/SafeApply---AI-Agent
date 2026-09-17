"""
SafeApply — AI Recruitment Scam Detector

Interactive Web Application built with Streamlit.

Demonstrates:
- GenAI
- RAG
- Agent orchestration
- ML classification
- Tool use
- Responsible AI
"""

import time

import streamlit as st

from agent import (
    analyze_job_offer,
    is_azure_openai_configured,
    is_github_models_configured,
)

from extractor import (
    is_azure_language_configured,
)

from search_indexer import (
    is_azure_configured
    as is_azure_search_configured,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title=(
        "SafeApply — AI Recruitment Scam Detector"
    ),
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# STYLING
# =========================================================

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
            max-width: 760px;
        }

        .risk-badge {
            display: inline-block;
            font-size: 0.95rem;
            font-weight: 600;
            padding: 0.25rem 0.85rem;
            border-radius: 6px;
            letter-spacing: 0.02em;
        }

        .badge-high {
            background-color: rgba(239, 68, 68, 0.16);
            color: #ef4444;
        }

        .badge-medium {
            background-color: rgba(245, 158, 11, 0.16);
            color: #f59e0b;
        }

        .badge-low {
            background-color: rgba(34, 197, 94, 0.16);
            color: #22c55e;
        }

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

        .attr-row b {
            opacity: 1;
        }

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


# =========================================================
# SAMPLE OFFERS
# =========================================================

PRESET_SAMPLES = {

    (
        "Select a preset sample or paste custom text..."
    ): "",

    (
        "🚨 High Risk Scam "
        "(Advance Fee & Fake Domain)"
    ): (
        "Congratulations! You have been selected at "
        "TechCorp Solutions for the role of Graduate "
        "Software Engineer.\n"
        "Annual package: INR 8,00,000 per annum.\n"
        "To confirm your placement slot and receive "
        "your formal appointment letter, please remit "
        "a refundable registration fee of Rs 1,499 "
        "via UPI within 2 hours.\n"
        "Send your payment confirmation screenshot "
        "immediately to hr.techcorp@gmail.com or your "
        "candidature will be permanently cancelled."
    ),

    (
        "✅ Legitimate Offer "
        "(Microsoft India Internship)"
    ): (
        "Dear Candidate,\n\n"
        "Following your technical interviews with our "
        "engineering team, we are pleased to offer you "
        "an internship at Microsoft India (R&D) Pvt. Ltd.\n\n"
        "Role: Software Engineering Intern\n"
        "Stipend: INR 50,000 per month\n"
        "Location: Hyderabad Campus\n\n"
        "Microsoft never charges any fees or security "
        "deposits at any stage of our recruitment process.\n"
        "Please review and sign your formal offer letter "
        "on the Microsoft Careers Portal: "
        "https://careers.microsoft.com.\n\n"
        "University Recruiting Team, Microsoft India\n"
        "Email: university-recruiting@microsoft.com"
    ),

    (
        "⚠️ Ambiguous Offer "
        "(Unverified Small Agency)"
    ): (
        "Hi,\n\n"
        "I found your profile on LinkedIn for our "
        "boutique digital marketing agency, Apex Media.\n"
        "We have an open junior web designer role. "
        "Salary is around INR 25,000 per month depending "
        "on your portfolio.\n"
        "Please reply with your resume and sample links "
        "if interested.\n\n"
        "Regards,\n"
        "Karan\n"
        "Email: karan.apexmedia@gmail.com"
    ),
}


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "### 🛡️ SafeApply"
    )

    st.caption(
        "Cloud service status"
    )

    if is_azure_openai_configured():

        foundry_status = (
            "🟢 Active — Azure AI Foundry"
        )

    elif is_github_models_configured():

        foundry_status = (
            "🟢 Active — GitHub Models"
        )

    else:

        foundry_status = (
            "🟡 Local mode"
        )

    search_status = (
        "🟢 Active"
        if is_azure_search_configured()
        else "🟡 Local RAG"
    )

    lang_status = (
        "🟢 Active"
        if is_azure_language_configured()
        else "🟡 Regex heuristics"
    )

    st.markdown(
        (
            "<div class='status-line'>"
            "<b>GenAI</b> — "
            f"{foundry_status}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='status-line'>"
            "<b>Search / RAG</b> — "
            f"{search_status}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='status-line'>"
            "<b>Language</b> — "
            f"{lang_status}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        (
            "<div class='status-line'>"
            "<b>ML Classifier</b> — "
            "🟢 Active (EMSCAD)"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.divider()

    st.caption(
        "4-Pillar Detection Architecture"
    )

    st.markdown(
        "1. **Rules Engine** — Domain & salary sanity\n"
        "2. **ML Classifier** — EMSCAD statistical model\n"
        "3. **Azure Search RAG** — Grounded scam patterns\n"
        "4. **Foundry GenAI** — Grounded explanation"
    )

    st.divider()

    st.caption(
        "SafeApply Recruitment Scam Detector"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    (
        '<div class="main-title">'
        "🛡️ SafeApply"
        "</div>"
    ),
    unsafe_allow_html=True,
)

st.markdown(
    (
        '<div class="sub-title">'
        "An AI recruitment-risk assistant combining "
        "machine learning, evidence-grounded RAG, "
        "domain and salary verification, deterministic "
        "risk fusion, and GenAI-based explanation."
        "</div>"
    ),
    unsafe_allow_html=True,
)


# =========================================================
# INPUT
# =========================================================

selected_preset = st.selectbox(
    "Try a sample, or paste your own offer below",
    options=list(
        PRESET_SAMPLES.keys()
    ),
    index=0,
    label_visibility="visible",
)


default_text = (
    PRESET_SAMPLES[
        selected_preset
    ]
    if selected_preset
    != (
        "Select a preset sample "
        "or paste custom text..."
    )
    else ""
)


offer_input = st.text_area(
    "Job offer text",
    value=default_text,
    height=190,
    placeholder=(
        "Paste the email, WhatsApp message, "
        "job description, or placement letter here..."
    ),
    label_visibility="collapsed",
)


analyze_button = st.button(
    "🔍 Analyze Offer",
    type="primary",
    use_container_width=False,
)


# =========================================================
# RESULT
# =========================================================

if analyze_button:

    if (
        not offer_input
        or len(
            offer_input.strip()
        ) < 15
    ):

        st.warning(
            "Please enter or select a valid "
            "job offer text to analyze."
        )

    else:

        with st.spinner(
            "Running extraction, ML classification, "
            "RAG retrieval, verification tools, "
            "and grounded synthesis..."
        ):

            start_time = (
                time.time()
            )

            result = (
                analyze_job_offer(
                    offer_input
                )
            )

            latency = (
                time.time()
                - start_time
            )

        risk_level = (
            result["risk_level"]
        )

        risk_score = (
            result["risk_score"]
        )

        badge_map = {
            "High": (
                "badge-high",
                "High risk",
            ),

            "Medium": (
                "badge-medium",
                "Medium risk",
            ),

            "Low": (
                "badge-low",
                "Low risk",
            ),
        }

        (
            badge_class,
            badge_label,
        ) = badge_map.get(
            risk_level,
            (
                "badge-medium",
                risk_level,
            ),
        )

        st.divider()

        # -------------------------------------------------
        # PRIMARY RESULT
        # -------------------------------------------------

        with st.container(
            border=True
        ):

            top = st.columns(
                [
                    3,
                    1,
                ]
            )

            with top[0]:

                st.markdown(
                    (
                        f'<span class="risk-badge '
                        f'{badge_class}">'
                        f"{badge_label}"
                        "</span>"
                    ),
                    unsafe_allow_html=True,
                )

                st.write(
                    result[
                        "explanation"
                    ]
                )

            with top[1]:

                st.metric(
                    "Risk score",
                    f"{risk_score}/100",
                )

            st.caption(
                (
                    f"Processed in {latency:.2f}s · "
                    f"{result['execution_mode']}"
                )
            )

        st.write("")

        # -------------------------------------------------
        # EXTRACTED DATA AND FLAGS
        # -------------------------------------------------

        col1, col2 = (
            st.columns(2)
        )

        with col1:

            st.markdown(
                (
                    '<div class="section-label">'
                    "Extracted attributes"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            with st.container(
                border=True
            ):

                extracted = (
                    result.get(
                        "extracted_data",
                        {},
                    )
                )

                st.markdown(
                    (
                        "<div class='attr-row'>"
                        "<b>Company</b> — "
                        f"{extracted.get('company_name', 'Not specified')}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                st.markdown(
                    (
                        "<div class='attr-row'>"
                        "<b>Salary</b> — "
                        f"{extracted.get('salary', 'Not specified')}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                st.markdown(
                    (
                        "<div class='attr-row'>"
                        "<b>Email</b> — "
                        f"{extracted.get('contact_email', 'Not specified')}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                st.markdown(
                    (
                        "<div class='attr-row'>"
                        "<b>Domain</b> — "
                        f"{extracted.get('contact_domain', 'Not specified')}"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )

                actions = (
                    extracted.get(
                        "requested_actions",
                        [],
                    )
                )

                if actions:

                    st.markdown(
                        (
                            "<div class='attr-row' "
                            "style='margin-top:0.4rem;'>"
                            "<b>Requested actions</b>"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )

                    for action in actions:

                        st.markdown(
                            (
                                "<div class='attr-row'>"
                                f"· {action}"
                                "</div>"
                            ),
                            unsafe_allow_html=True,
                        )

                else:

                    st.markdown(
                        (
                            "<div class='attr-row' "
                            "style='margin-top:0.4rem;'>"
                            "<b>Requested actions</b> — "
                            "none flagged"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )

        with col2:

            st.markdown(
                (
                    '<div class="section-label">'
                    "Flagged indicators"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

            with st.container(
                border=True
            ):

                flags = (
                    result.get(
                        "identified_red_flags",
                        [],
                    )
                )

                no_flag_messages = {
                    (
                        "No scam red flags detected."
                    ),
                    (
                        "No strong scam red flags detected "
                        "by the current checks."
                    ),
                }

                if (
                    flags
                    and not (
                        len(flags) == 1
                        and flags[0]
                        in no_flag_messages
                    )
                ):

                    for flag in flags:

                        st.markdown(
                            (
                                "<div class='attr-row'>"
                                f"🚩 {flag}"
                                "</div>"
                            ),
                            unsafe_allow_html=True,
                        )

                else:

                    st.markdown(
                        (
                            "<div class='attr-row'>"
                            "No strong red flags identified "
                            "by the current checks."
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )

        # -------------------------------------------------
        # TOOL OUTPUTS
        # -------------------------------------------------

        st.write("")

        st.markdown(
            (
                '<div class="section-label">'
                "Agent tool outputs"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        tool_tabs = st.tabs(
            [
                "RAG red-flag checker",
                "Domain verification",
                "Salary sanity check",
                "EMSCAD ML Classifier",
            ]
        )

        # -------------------------------------------------
        # RAG TAB
        # -------------------------------------------------

        with tool_tabs[0]:

            rag_matches = (
                result[
                    "tool_outputs"
                ].get(
                    "rag_matches",
                    [],
                )
            )

            if rag_matches:

                st.caption(
                    (
                        f"{len(rag_matches)} grounded "
                        "pattern reference(s) retrieved "
                        "from the scam-pattern knowledge base"
                    )
                )

                for match in rag_matches:

                    with st.container(
                        border=True
                    ):

                        st.markdown(
                            (
                                f"**{match.get('category', 'Unknown')}** "
                                "&nbsp;·&nbsp; "
                                "Search Score "
                                f"`{match.get('score', 0)}`"
                            )
                        )

                        st.markdown(
                            "**Retrieved Pattern**"
                        )

                        st.caption(
                            match.get(
                                "pattern",
                                (
                                    "No reference "
                                    "pattern available."
                                ),
                            )
                        )

                        evidence = (
                            match.get(
                                "evidence",
                                [],
                            )
                        )

                        if evidence:

                            st.markdown(
                                (
                                    "**Observed Evidence "
                                    "in This Offer**"
                                )
                            )

                            for item in evidence:

                                st.caption(
                                    f"• {item}"
                                )

                        else:

                            st.caption(
                                (
                                    "No directly grounded evidence "
                                    "was attached to this reference."
                                )
                            )

            else:

                st.caption(
                    (
                        "No grounded scam-pattern references "
                        "were identified in the knowledge base."
                    )
                )

        # -------------------------------------------------
        # DOMAIN TAB
        # -------------------------------------------------

        with tool_tabs[1]:

            d_check = (
                result[
                    "tool_outputs"
                ].get(
                    "domain_verification",
                    {},
                )
            )

            st.markdown(
                (
                    "**Status** — "
                    f"{d_check.get('status', 'N/A')}"
                )
            )

            st.markdown(
                (
                    "**Severity** — "
                    f"{d_check.get('severity', 'LOW')}"
                )
            )

            st.caption(
                d_check.get(
                    "message",
                    "",
                )
            )

        # -------------------------------------------------
        # SALARY TAB
        # -------------------------------------------------

        with tool_tabs[2]:

            s_check = (
                result[
                    "tool_outputs"
                ].get(
                    "salary_sanity",
                    {},
                )
            )

            st.markdown(
                (
                    "**Flagged** — "
                    f"{s_check.get('is_flagged', False)}"
                )
            )

            st.markdown(
                (
                    "**Claimed compensation** — "
                    f"{s_check.get('claimed_salary', 'N/A')}"
                )
            )

            st.caption(
                s_check.get(
                    "message",
                    "",
                )
            )

        # -------------------------------------------------
        # ML TAB
        # -------------------------------------------------

        with tool_tabs[3]:

            ml_out = (
                result[
                    "tool_outputs"
                ].get(
                    "ml_classifier",
                    {},
                )
            )

            ml_prob = float(
                ml_out.get(
                    "fraud_probability_pct",
                    0.0,
                )
                or 0.0
            )

            ml_risk = (
                ml_out.get(
                    "risk_level",
                    "Low",
                )
            )

            ml_verdict = (
                ml_out.get(
                    "verdict",
                    "N/A",
                )
            )

            mcol1, mcol2 = (
                st.columns(
                    [
                        1,
                        2,
                    ]
                )
            )

            with mcol1:

                st.metric(
                    (
                        "EMSCAD Fraud "
                        "Probability"
                    ),
                    f"{ml_prob:.1f}%",
                )

                st.markdown(
                    (
                        "**ML Risk Band** — "
                        f"`{ml_risk}`"
                    )
                )

                st.markdown(
                    (
                        "**Classifier Decision** — "
                        f"`{ml_verdict}`"
                    )
                )

                st.caption(
                    (
                        "Decision Threshold: "
                        f"`{ml_out.get('optimal_threshold', 0.70)}`"
                    )
                )

            with mcol2:

                st.progress(
                    min(
                        max(
                            ml_prob / 100.0,
                            0.0,
                        ),
                        1.0,
                    )
                )

                risk_tokens = (
                    ml_out.get(
                        "top_risk_tokens",
                        [],
                    )
                )

                legit_tokens = (
                    ml_out.get(
                        "top_legit_tokens",
                        [],
                    )
                )

                if risk_tokens:

                    formatted = ", ".join(
                        f"`{token}`"
                        for token
                        in risk_tokens
                    )

                    st.markdown(
                        (
                            "**Model-Associated "
                            "Risk Terms**: "
                            f"{formatted}"
                        )
                    )

                if legit_tokens:

                    formatted = ", ".join(
                        f"`{token}`"
                        for token
                        in legit_tokens
                    )

                    st.markdown(
                        (
                            "**Model-Associated "
                            "Legitimacy Terms**: "
                            f"{formatted}"
                        )
                    )

                st.caption(
                    (
                        "The probability is an advisory "
                        "machine-learning signal. It should "
                        "be interpreted together with the "
                        "domain, salary, RAG, and direct-evidence "
                        "checks rather than as independent proof "
                        "that an offer is fraudulent."
                    )
                )

                st.caption(
                    (
                        "Model: "
                        f"{ml_out.get('model_version', 'SafeApply-EMSCAD')}"
                    )
                )

        # -------------------------------------------------
        # RESPONSIBLE AI
        # -------------------------------------------------

        st.markdown(
            f"""
            <div class="disclaimer-box">
                <b>Responsible AI notice</b> —
                {result['responsible_ai_disclaimer']}
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# LANDING STATE
# =========================================================

else:

    st.info(
        (
            "Pick a sample above and click "
            "**Analyze Offer** to see it in action."
        )
    )

    st.write("")

    f1, f2, f3 = (
        st.columns(3)
    )

    with f1:

        with st.container(
            border=True
        ):

            st.markdown(
                "**Hybrid Detection**"
            )

            st.caption(
                (
                    "Combines deterministic evidence checks, "
                    "EMSCAD machine learning, and Azure AI "
                    "Search rather than relying on an LLM alone."
                )
            )

    with f2:

        with st.container(
            border=True
        ):

            st.markdown(
                "**Agent Orchestration**"
            )

            st.caption(
                (
                    "Coordinates extraction, RAG retrieval, "
                    "domain analysis, salary analysis, ML "
                    "classification, and deterministic risk fusion."
                )
            )

    with f3:

        with st.container(
            border=True
        ):

            st.markdown(
                "**Responsible AI**"
            )

            st.caption(
                (
                    "The final explanation is grounded in "
                    "observed evidence and the system remains "
                    "advisory rather than declaring an employer "
                    "or recruiter fraudulent."
                )
            )