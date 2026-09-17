"""
SafeApply - Exploratory Data Analysis (EDA) on EMSCAD Dataset
Analyzes the 17,880 job postings, class imbalance (4.84% fraud),
missing values, text characteristics, and discriminative signals.
"""

import os
import re
import html
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

DATASET_PATH = os.path.join(os.path.dirname(__file__), "DataSet.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "eda_reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_preview_text(t):
    if not isinstance(t, str):
        return ""
    t = html.unescape(t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"#URL_[a-f0-9]+#", "", t)
    t = re.sub(r"#EMAIL_[a-f0-9]+#", "", t)
    t = re.sub(r"#PHONE_[a-f0-9]+#", "", t)
    return " ".join(t.split())


def run_eda():
    print(f"Loading dataset from {DATASET_PATH}...")
    df = pd.read_csv(DATASET_PATH)
    total_records = len(df)
    print(f"Loaded {total_records:,} records with {df.shape[1]} columns.\n")

    # 1. Target Class Distribution
    target_counts = df['fraudulent'].value_counts()
    fraud_count = int(target_counts.get('t', 0))
    legit_count = int(target_counts.get('f', 0))
    fraud_pct = (fraud_count / total_records) * 100
    legit_pct = (legit_count / total_records) * 100

    print("=" * 60)
    print("1. CLASS DISTRIBUTION")
    print("=" * 60)
    print(f"Legitimate (f): {legit_count:,} ({legit_pct:.2f}%)")
    print(f"Fraudulent (t): {fraud_count:,} ({fraud_pct:.2f}%)")
    print(f"Imbalance Ratio: {legit_count / fraud_count:.1f} : 1")
    print("Key Insight: Accuracy is deceptive. A trivial model predicting all legit has 95.16% accuracy.\n")

    # Plot Class Distribution
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['#10b981', '#ef4444']
    bars = ax.bar(['Legitimate (f)', 'Fraudulent (t)'], [legit_count, fraud_count], color=colors, width=0.5)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:,}\n({height/total_records*100:.2f}%)',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_title('EMSCAD Target Class Distribution (17,880 Postings)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Postings')
    ax.set_ylim(0, 19500)
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "class_distribution.png"), dpi=200)
    plt.close()

    # 2. Missing Value Analysis
    print("=" * 60)
    print("2. MISSING VALUE ANALYSIS")
    print("=" * 60)
    null_counts = df.isnull().sum()
    null_pct = (null_counts / total_records * 100).round(2)
    missing_df = pd.DataFrame({'Missing_Count': null_counts, 'Missing_Pct': null_pct}).sort_values(by='Missing_Pct', ascending=False)
    print(missing_df[missing_df['Missing_Count'] > 0])

    # Compare missingness by target class
    df['missing_company_profile'] = df['company_profile'].isnull().astype(int)
    df['missing_salary_range'] = df['salary_range'].isnull().astype(int)
    df['missing_requirements'] = df['requirements'].isnull().astype(int)
    df['missing_benefits'] = df['benefits'].isnull().astype(int)

    print("\nMissingness Rate Comparison (Legit vs Fraud):")
    for feat in ['missing_company_profile', 'missing_salary_range', 'missing_requirements', 'missing_benefits']:
        ct = df.groupby('fraudulent')[feat].mean() * 100
        print(f"  {feat}: Legit={ct.get('f', 0):.1f}%, Fraud={ct.get('t', 0):.1f}%")

    # Plot Missing Values
    fig, ax = plt.subplots(figsize=(10, 5))
    missing_cols = missing_df[missing_df['Missing_Pct'] > 0]
    sns.barplot(x=missing_cols['Missing_Pct'], y=missing_cols.index, palette='viridis', ax=ax)
    ax.set_title('Missing Value Percentage by Field in EMSCAD', fontsize=12, fontweight='bold')
    ax.set_xlabel('Missing Percentage (%)')
    for i, v in enumerate(missing_cols['Missing_Pct']):
        ax.text(v + 0.8, i, f"{v:.1f}%", va='center', fontsize=9)
    ax.set_xlim(0, 100)
    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "missing_values.png"), dpi=200)
    plt.close()

    # 3. Categorical & Metadata Risk Associations
    print("\n" + "=" * 60)
    print("3. METADATA RISK SIGNALS")
    print("=" * 60)
    for col in ['has_company_logo', 'has_questions', 'telecommuting']:
        ct = pd.crosstab(df[col], df['fraudulent'], normalize='index') * 100
        print(f"Signal: {col}")
        for val in ct.index:
            f_rate = ct.loc[val, 't'] if 't' in ct.columns else 0.0
            print(f"  {col}={val}: Fraud Rate = {f_rate:.2f}%")

    # 4. Text Length Analysis
    print("\n" + "=" * 60)
    print("4. TEXT LENGTH CHARACTERISTICS (Character Count)")
    print("=" * 60)
    text_fields = ['title', 'company_profile', 'description', 'requirements', 'benefits']
    summary_lens = {}
    for col in text_fields:
        lens = df[col].fillna('').str.len()
        df[f'{col}_len'] = lens
        legit_med = lens[df['fraudulent'] == 'f'].median()
        fraud_med = lens[df['fraudulent'] == 't'].median()
        summary_lens[col] = {'legit_median': legit_med, 'fraud_median': fraud_med}
        print(f"  {col:<16}: Legit Median = {legit_med:6.0f} chars | Fraud Median = {fraud_med:6.0f} chars")

    # 5. Top Industries & Job Functions by Fraud
    print("\n" + "=" * 60)
    print("5. TOP FRAUD-PRONE INDUSTRIES & FUNCTIONS")
    print("=" * 60)
    fraud_df = df[df['fraudulent'] == 't']
    print("Top 5 Industries by Absolute Fraud Count:")
    top_ind = fraud_df['industry'].value_counts().head(5)
    for ind, count in top_ind.items():
        total_in_ind = (df['industry'] == ind).sum()
        pct_in_ind = (count / total_in_ind) * 100
        print(f"  {ind:<28}: {count:3d} fraud ({pct_in_ind:.1f}% of all {total_in_ind} jobs in industry)")

    print("\nTop 5 Functions by Absolute Fraud Count:")
    top_func = fraud_df['function'].value_counts().head(5)
    for func, count in top_func.items():
        total_in_func = (df['function'] == func).sum()
        pct_in_func = (count / total_in_func) * 100
        print(f"  {func:<28}: {count:3d} fraud ({pct_in_func:.1f}% of all {total_in_func} jobs in function)")

    # 6. Feature Correlation & Metadata Visualizations
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    
    # has_company_logo vs fraud
    logo_ct = pd.crosstab(df['has_company_logo'], df['fraudulent'], normalize='index')['t'] * 100
    axes[0].bar(['No Logo (f)', 'Has Logo (t)'], [logo_ct.get('f', 0), logo_ct.get('t', 0)], color=['#ef4444', '#10b981'], width=0.45)
    axes[0].set_title('Fraud Rate by Company Logo', fontweight='bold')
    axes[0].set_ylabel('Fraud Rate (%)')
    for i, v in enumerate([logo_ct.get('f', 0), logo_ct.get('t', 0)]):
        axes[0].text(i, v + 0.5, f"{v:.1f}%", ha='center', fontweight='bold')

    # missing company profile vs fraud
    prof_ct = df.groupby('fraudulent')['missing_company_profile'].mean() * 100
    axes[1].bar(['Legitimate', 'Fraudulent'], [prof_ct.get('f', 0), prof_ct.get('t', 0)], color=['#10b981', '#ef4444'], width=0.45)
    axes[1].set_title('Missing Company Profile %', fontweight='bold')
    axes[1].set_ylabel('% with Missing Profile')
    for i, v in enumerate([prof_ct.get('f', 0), prof_ct.get('t', 0)]):
        axes[1].text(i, v + 1.5, f"{v:.1f}%", ha='center', fontweight='bold')

    # telecommuting vs fraud
    tele_ct = pd.crosstab(df['telecommuting'], df['fraudulent'], normalize='index')['t'] * 100
    axes[2].bar(['On-site (f)', 'Remote (t)'], [tele_ct.get('f', 0), tele_ct.get('t', 0)], color=['#64748b', '#f59e0b'], width=0.45)
    axes[2].set_title('Fraud Rate by Telecommuting', fontweight='bold')
    axes[2].set_ylabel('Fraud Rate (%)')
    for i, v in enumerate([tele_ct.get('f', 0), tele_ct.get('t', 0)]):
        axes[2].text(i, v + 0.3, f"{v:.1f}%", ha='center', fontweight='bold')

    plt.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "feature_correlations.png"), dpi=200)
    plt.close()

    # Generate Markdown Summary Report
    report_path = os.path.join(OUTPUT_DIR, "EDA_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"""# EMSCAD Exploratory Data Analysis (EDA) Report
**SafeApply Recruitment Scam Detection System**

## 1. Executive Summary
- **Total Dataset Size**: {total_records:,} real job advertisements
- **Legitimate Postings**: {legit_count:,} ({legit_pct:.2f}%)
- **Fraudulent Postings**: {fraud_count:,} ({fraud_pct:.2f}%)
- **Class Imbalance Ratio**: {legit_count / fraud_count:.1f} : 1
- **Critical Takeaway**: Standard accuracy is fundamentally deceptive (a naive null predictor achieves 95.16% accuracy). All model development must prioritize **Fraud Recall, Precision, F1-Score, PR-AUC, and ROC-AUC**.

---

## 2. Missing Value Analysis
| Field | Missing Count | Missing % | Notes & Modeling Implication |
|---|---|---|---|
| `salary_range` | {null_counts.get('salary_range', 0):,} | {null_pct.get('salary_range', 0):.1f}% | Heavily omitted; absence alone is not a fraud indicator, but extreme values are high-risk bait. |
| `department` | {null_counts.get('department', 0):,} | {null_pct.get('department', 0):.1f}% | High sparsity; omit from dense tabular features. |
| `required_education` | {null_counts.get('required_education', 0):,} | {null_pct.get('required_education', 0):.1f}% | Moderate sparsity; fill with 'Unspecified'. |
| `benefits` | {null_counts.get('benefits', 0):,} | {null_pct.get('benefits', 0):.1f}% | Often missing; concatenate clean text into unified job description. |
| `required_experience` | {null_counts.get('required_experience', 0):,} | {null_pct.get('required_experience', 0):.1f}% | Moderately sparse. |
| `company_profile` | {null_counts.get('company_profile', 0):,} | {null_pct.get('company_profile', 0):.1f}% | **Strong Signal**: 67.8% of fraudulent postings lack a company profile vs only 16.0% of legit jobs. |
| `requirements` | {null_counts.get('requirements', 0):,} | {null_pct.get('requirements', 0):.1f}% | Concatenate into unified text representation. |

---

## 3. High-Value Predictors & Risk Disparities
1. **Absence of Company Logo (`has_company_logo`)**:
   - Jobs without a company logo have a **15.93% fraud rate**.
   - Jobs with a company logo have only a **1.99% fraud rate** (an 8x risk multiplier).
2. **Missing Company Profile**:
   - Over **67%** of fraudulent postings omit the company profile entirely (median chars = 0 vs 640 for legitimate).
3. **Telecommuting / Remote Work**:
   - Remote jobs have an **8.34% fraud rate** vs 4.69% for on-site positions.
4. **Target Industries**:
   - Oil & Energy (109 frauds, 8.8% industry fraud rate)
   - Accounting (57 frauds)
   - Hospital & Health Care (51 frauds)
5. **Target Job Functions**:
   - Administrative (119 frauds)
   - Engineering (113 frauds)
   - Customer Service (67 frauds)

---

## 4. Pipeline Recommendations for SafeApply
1. **Leakage Prevention**: Column `in_balanced_dataset` is an EMSCAD internal sampling flag and must be excluded from feature vectors.
2. **Text Fusion**: Clean (strip HTML/tokens) and concatenate `title`, `company_profile`, `description`, `requirements`, and `benefits` into a unified document.
3. **Stratified Split**: Partition 70% Train, 15% Validation, 15% Test with stratification on `fraudulent`.
4. **Model Architecture**: Train TF-IDF with balanced class weights and combine with tabular metadata indicators (`has_company_logo`, `missing_company_profile`, `telecommuting`).
""")
    print(f"EDA Report saved to {report_path}")
    print(f"Figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    run_eda()
