# EMSCAD Exploratory Data Analysis (EDA) Report
**SafeApply Recruitment Scam Detection System**

## 1. Executive Summary
- **Total Dataset Size**: 17,880 real job advertisements
- **Legitimate Postings**: 17,014 (95.16%)
- **Fraudulent Postings**: 866 (4.84%)
- **Class Imbalance Ratio**: 19.6 : 1
- **Critical Takeaway**: Standard accuracy is fundamentally deceptive (a naive null predictor achieves 95.16% accuracy). All model development must prioritize **Fraud Recall, Precision, F1-Score, PR-AUC, and ROC-AUC**.

---

## 2. Missing Value Analysis
| Field | Missing Count | Missing % | Notes & Modeling Implication |
|---|---|---|---|
| `salary_range` | 15,012 | 84.0% | Heavily omitted; absence alone is not a fraud indicator, but extreme values are high-risk bait. |
| `department` | 11,547 | 64.6% | High sparsity; omit from dense tabular features. |
| `required_education` | 8,105 | 45.3% | Moderate sparsity; fill with 'Unspecified'. |
| `benefits` | 7,196 | 40.2% | Often missing; concatenate clean text into unified job description. |
| `required_experience` | 7,050 | 39.4% | Moderately sparse. |
| `company_profile` | 3,308 | 18.5% | **Strong Signal**: 67.8% of fraudulent postings lack a company profile vs only 16.0% of legit jobs. |
| `requirements` | 2,689 | 15.0% | Concatenate into unified text representation. |

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
