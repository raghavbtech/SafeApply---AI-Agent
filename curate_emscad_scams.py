"""
SafeApply - EMSCAD Historical Scam Curator for Azure AI Search RAG
Extracts representative, high-signal fraudulent job postings from EMSCAD (17,880 postings)
and formats them as structured RAG reference patterns.
"""

import os
import re
import html
import json
import pandas as pd

DATASET_PATH = os.path.join(os.path.dirname(__file__), "DataSet.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "emscad_scam_patterns.json")
MERGED_PATH = os.path.join(os.path.dirname(__file__), "scam_patterns.json")


def clean_text(t):
    if not isinstance(t, str):
        return ""
    t = html.unescape(t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"#URL_[a-f0-9]+#", "http://careers-portal.com", t)
    t = re.sub(r"#EMAIL_[a-f0-9]+#", "hr-recruiting@gmail.com", t)
    t = re.sub(r"#PHONE_[a-f0-9]+#", "+1-800-555-0199", t)
    t = t.replace("\ufffd", " ")
    return " ".join(t.split())


def curate_emscad_patterns():
    print(f"Reading {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)
    fraud_df = df[df["fraudulent"].astype(str).str.lower() == "t"]
    print(f"Total fraudulent postings available: {len(fraud_df)}")

    curated = []

    # 1. Oil & Gas Engineering Spoofing (109 frauds in dataset)
    oil = fraud_df[fraud_df["industry"] == "Oil & Energy"]
    for i in range(min(3, len(oil))):
        row = oil.iloc[i]
        title = str(row["title"]).strip()
        desc = clean_text(row["description"])[:280]
        reqs = clean_text(row["requirements"])[:120]
        curated.append({
            "id": f"emscad_oil_{i+1:02d}",
            "category": "vague_role_process",
            "pattern": f"EMSCAD Real Scam: Offshore Oil & Gas Engineering Contract Spoof ({title})",
            "example_text": f"Role: {title}. {desc} Qualifications: {reqs}",
            "risk_weight": "high",
        })

    # 2. Administrative & Data Entry Work-From-Home (119 frauds in dataset)
    admin = fraud_df[fraud_df["function"] == "Administrative"]
    for i in range(min(3, len(admin))):
        row = admin.iloc[i]
        title = str(row["title"]).strip()
        desc = clean_text(row["description"])[:280]
        curated.append({
            "id": f"emscad_admin_{i+1:02d}",
            "category": "salary_ratio",
            "pattern": f"EMSCAD Real Scam: Unrealistic Work-From-Home Administrative / Data Entry ({title})",
            "example_text": f"Position: {title}. {desc}",
            "risk_weight": "high",
        })

    # 3. Medical / Healthcare Billing & Clerk (51 frauds in dataset)
    health = fraud_df[fraud_df["industry"] == "Hospital & Health Care"]
    for i in range(min(3, len(health))):
        row = health.iloc[i]
        title = str(row["title"]).strip()
        desc = clean_text(row["description"])[:280]
        curated.append({
            "id": f"emscad_health_{i+1:02d}",
            "category": "premature_personal_info",
            "pattern": f"EMSCAD Real Scam: Remote Medical Clerk / Billing Advance-Fee Bait ({title})",
            "example_text": f"Position: {title}. {desc}",
            "risk_weight": "high",
        })

    # 4. Accounting & Payroll Fraud (57 frauds in dataset)
    acct = fraud_df[fraud_df["industry"] == "Accounting"]
    for i in range(min(3, len(acct))):
        row = acct.iloc[i]
        title = str(row["title"]).strip()
        desc = clean_text(row["description"])[:280]
        curated.append({
            "id": f"emscad_acct_{i+1:02d}",
            "category": "fake_check_equipment",
            "pattern": f"EMSCAD Real Scam: Accounting / Payroll Assistant Check Re-routing Scheme ({title})",
            "example_text": f"Position: {title}. {desc}",
            "risk_weight": "high",
        })

    # 5. Customer Service & Virtual Call Agent (67 frauds in dataset)
    cs = fraud_df[fraud_df["function"] == "Customer Service"]
    for i in range(min(3, len(cs))):
        row = cs.iloc[i]
        title = str(row["title"]).strip()
        desc = clean_text(row["description"])[:280]
        curated.append({
            "id": f"emscad_cs_{i+1:02d}",
            "category": "urgency_pressure",
            "pattern": f"EMSCAD Real Scam: Instant Hiring Virtual Customer Support Agent ({title})",
            "example_text": f"Position: {title}. {desc}",
            "risk_weight": "medium",
        })

    print(f"Generated {len(curated)} curated EMSCAD historical scam patterns.")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(curated, f, indent=2)
    print(f"Saved standalone EMSCAD patterns to {OUTPUT_PATH}")

    # Merge into scam_patterns.json (preserving base rule patterns and appending EMSCAD patterns)
    base_patterns = []
    if os.path.exists(MERGED_PATH):
        with open(MERGED_PATH, "r", encoding="utf-8") as f:
            base_patterns = json.load(f)

    # Filter out existing emscad patterns if re-run
    filtered_base = [p for p in base_patterns if not p.get("id", "").startswith("emscad_")]
    merged = filtered_base + curated

    with open(MERGED_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"Updated {MERGED_PATH} with {len(merged)} total patterns ({len(filtered_base)} rule-based + {len(curated)} EMSCAD historical cases).")


if __name__ == "__main__":
    curate_emscad_patterns()
