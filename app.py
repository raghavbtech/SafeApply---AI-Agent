"""
SafeApply — AI Recruitment Scam Detector
Interactive Web Application built with Streamlit
Demonstrating GenAI, RAG, Agent Orchestration, Tool Use, and Responsible AI.
"""

import streamlit as st
import time
from agent import analyze_job_offer, is_azure_openai_configured
from extractor import is_azure_language_configured
from search_indexer import is_azure_configured as is_azure_search_configured

# Page configuration
st.set_page_config(
    page_title="SafeApply — AI Recruitment Scam Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #0078D4 0%, #00B4D8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .risk-card {
        padding: 1.2rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        border: 1px solid #e0e0e0;
    }
    .risk-badge {
        display: inline-block;
        font-size: 1.3rem;
        font-weight: 700;
        padding: 0.35rem 1.2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 0.8rem;
    }
    .badge-high {
        background-color: #D32F2F;
    }
    .badge-medium {
        background-color: #F57C00;
    }
    .badge-low {
        background-color: #2E7D32;
    }
    .metric-box {
        background-color: #F8F9FA;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        border-left: 4px solid #0078D4;
        margin-bottom: 0.5rem;
    }
    .disclaimer-card {
        background-color: #EFF6FF;
        border-left: 5px solid #0078D4;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        color: #1E3A8A;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Preset sample offers for 1-click evaluation
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
    )
}

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/shield.png", width=64)
    st.markdown("### SafeApply Cloud Status")
    st.markdown("Azure Services Integration for Student Evaluation:")

    # Service Status Indicators
    foundry_status = "🟢 Active" if is_azure_openai_configured() else "🟡 Local Fallback Mode"
    search_status = "🟢 Active" if is_azure_search_configured() else "🟡 Local RAG Mode"
    lang_status = "🟢 Active" if is_azure_language_configured() else "🟡 Regex Heuristics Mode"

    st.markdown(f"- **Azure AI Foundry (GPT-4o-mini)**: {foundry_status}")
    st.markdown(f"- **Azure AI Search (F0 Tier)**: {search_status}")
    st.markdown(f"- **Azure AI Language (F0 Tier)**: {lang_status}")

    st.markdown("---")
    st.markdown("### AI-103 Concepts Demonstrated")
    st.markdown("1. **GenAI**: GPT-4o-mini Risk Synthesis")
    st.markdown("2. **RAG**: Azure AI Search Similarity Retrieval")
    st.markdown("3. **Agent Orchestration**: Multi-Tool Coordination")
    st.markdown("4. **Tool Use**: Domain & Salary Sanity Checkers")
    st.markdown("5. **Responsible AI**: False-Positive Resistance")

    st.markdown("---")
    st.markdown("**Version:** 1.0.0 (Azure Evaluation Build)")
    st.markdown("Project: SafeApply Recruitment Scam Detector")


# ----------------- MAIN HEADER -----------------
st.markdown('<div class="main-title">🛡️ SafeApply — AI Recruitment Scam Detector</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Intelligent AI agent that analyzes job offers, flags fraud indicators (fake fees, mismatched domains, unrealistic salaries), and gives students a clear risk score with plain-English advisory explanations.</div>',
    unsafe_allow_html=True,
)

# ----------------- INPUT SECTION -----------------
col_preset, col_clear = st.columns([3, 1])
with col_preset:
    selected_preset = st.selectbox(
        "Choose a sample offer to test instantly, or type your own below:",
        options=list(PRESET_SAMPLES.keys()),
        index=0
    )

default_text = PRESET_SAMPLES[selected_preset] if selected_preset != "Select a preset sample or paste custom text..." else ""

offer_input = st.text_area(
    "Paste the full job offer email, message, or placement letter text here:",
    value=default_text,
    height=180,
    placeholder="Paste email text, WhatsApp message, or campus placement offer letter here..."
)

analyze_button = st.button("🔍 Analyze Offer for Scam Red Flags", type="primary", use_container_width=True)

# ----------------- ANALYSIS RESULTS -----------------
if analyze_button:
    if not offer_input or len(offer_input.strip()) < 15:
        st.warning("Please enter or select a valid job offer text to analyze.")
    else:
        with st.spinner("🤖 SafeApply Agent executing extraction, RAG pattern retrieval, and GenAI synthesis..."):
            start_time = time.time()
            result = analyze_job_offer(offer_input)
            latency = time.time() - start_time

        risk_level = result["risk_level"]
        risk_score = result["risk_score"]

        # Badge styling based on risk verdict
        if risk_level == "High":
            badge_class = "badge-high"
            badge_icon = "🚨 HIGH RISK"
            border_color = "#D32F2F"
        elif risk_level == "Medium":
            badge_class = "badge-medium"
            badge_icon = "⚠️ MEDIUM RISK"
            border_color = "#F57C00"
        else:
            badge_class = "badge-low"
            badge_icon = "✅ LOW RISK"
            border_color = "#2E7D32"

        st.markdown("---")
        st.markdown(f"### Assessment Verdict")

        # Top Banner Card
        st.markdown(f"""
        <div class="risk-card" style="border-left: 8px solid {border_color};">
            <span class="risk-badge {badge_class}">{badge_icon} (Risk Score: {risk_score}/100)</span>
            <p style="font-size: 1.1rem; line-height: 1.6; margin-top: 0.5rem;"><b>Summary:</b> {result['explanation']}</p>
            <p style="font-size: 0.85rem; color: #666;">⚡ Processed in {latency:.2f}s via <b>{result['execution_mode']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        # Three-column layout for details
        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### 📋 Extracted Offer Attributes")
            extracted = result.get("extracted_data", {})
            st.markdown(f"**Company Name:** `{extracted.get('company_name', 'Not specified')}`")
            st.markdown(f"**Offered Salary:** `{extracted.get('salary', 'Not specified')}`")
            st.markdown(f"**Contact Email:** `{extracted.get('contact_email', 'Not specified')}`")
            st.markdown(f"**Domain:** `{extracted.get('contact_domain', 'Not specified')}`")
            
            actions = extracted.get("requested_actions", [])
            if actions:
                st.markdown("**Identified Action Requests:**")
                for act in actions:
                    st.markdown(f"- {act}")
            else:
                st.markdown("**Identified Action Requests:** `None flagged`")

        with col2:
            st.markdown("#### 🚩 Flagged Red Indicators")
            flags = result.get("identified_red_flags", [])
            if flags and flags != ["No scam red flags detected."]:
                for flag in flags:
                    st.error(f"• {flag}")
            else:
                st.success("• No scam red flags identified. Communication pattern appears standard.")

        # Agent Tools Drilldown
        st.markdown("---")
        st.markdown("#### 🛠️ AI Agent Tools Output Drilldown")

        tool_tabs = st.tabs(["Tool 1: RAG Red-Flag Checker", "Tool 2: Domain Verification", "Tool 3: Salary Sanity Check"])

        with tool_tabs[0]:
            rag_matches = result["tool_outputs"].get("rag_matches", [])
            if rag_matches:
                st.write(f"Matched **{len(rag_matches)}** patterns from the Azure AI Search Recruitment Fraud Knowledge Base:")
                for m in rag_matches:
                    st.info(f"**Category:** `{m['category']}` | **Match Confidence:** `{m['score']}`\n\n**Pattern:** {m['pattern']}")
            else:
                st.write("No matching scam patterns identified in knowledge base.")

        with tool_tabs[1]:
            d_check = result["tool_outputs"].get("domain_verification", {})
            st.write(f"**Verification Status:** `{d_check.get('status', 'N/A')}`")
            st.write(f"**Severity Level:** `{d_check.get('severity', 'LOW')}`")
            st.write(f"**Agent Evaluation:** {d_check.get('message', '')}")

        with tool_tabs[2]:
            s_check = result["tool_outputs"].get("salary_sanity", {})
            st.write(f"**Flagged Anomaly:** `{s_check.get('is_flagged', False)}`")
            st.write(f"**Claimed Compensation:** `{s_check.get('claimed_salary', 'N/A')}`")
            st.write(f"**Agent Evaluation:** {s_check.get('message', '')}")

        # Responsible AI Advisory Disclaimer Banner
        st.markdown(f"""
        <div class="disclaimer-card">
            <b>⚖️ Responsible AI Notice:</b> {result['responsible_ai_disclaimer']}
        </div>
        """, unsafe_allow_html=True)

else:
    # Initial landing guide
    st.info("💡 **Quick Start for Evaluators:** Pick one of the sample presets in the dropdown above and click **Analyze Offer** to test live.")
    
    col_feat1, col_feat2, col_feat3 = st.columns(3)
    with col_feat1:
        st.markdown("### 🔍 RAG Knowledge Base")
        st.write("Cross-references offer text against 18+ curated recruitment fraud patterns indexed in Azure AI Search.")
    with col_feat2:
        st.markdown("### 🤖 Agentic Orchestration")
        st.write("Coordinates specialized extraction, domain verification, and compensation sanity tools seamlessly.")
    with col_feat3:
        st.markdown("### ⚖️ Responsible AI Guardrails")
        st.write("Built-in false-positive resistance protects legitimate corporate recruiters with cautious advisory phrasing.")
