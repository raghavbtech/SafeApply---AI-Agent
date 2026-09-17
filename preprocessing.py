"""
SafeApply - Data Cleaning & Preprocessing Pipeline
Handles text normalization, entity unescaping, token scrubbing,
metadata feature engineering, and stratified train/val/test splitting.
"""

import os
import re
import html
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

DATASET_PATH = os.path.join(os.path.dirname(__file__), "DataSet.csv")


def clean_text(text: str) -> str:
    """
    Sanitize raw job posting text:
    - HTML entity unescaping
    - HTML tag stripping
    - Token normalization (#URL_...#, #EMAIL_...#, #PHONE_...#)
    - Punctuation and whitespace normalization
    """
    if not text or not isinstance(text, str):
        return ""

    # Unescape HTML entities (e.g., &amp; -> &, &lt; -> <)
    text = html.unescape(text)

    # Strip HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Replace obfuscated/masked tokens with generic semantic indicators
    text = re.sub(r"#URL_[a-f0-9]+#", " httpurl ", text)
    text = re.sub(r"#EMAIL_[a-f0-9]+#", " emailaddr ", text)
    text = re.sub(r"#PHONE_[a-f0-9]+#", " phonenum ", text)

    # Remove non-ascii replacement characters often found in web scraped text
    text = text.replace("\ufffd", " ")

    # Normalize punctuation and extra whitespace
    text = re.sub(r"[^\w\s\$\€\£\₹]", " ", text)
    return " ".join(text.split()).lower()


def combine_job_text(item: dict) -> str:
    """
    Construct a unified, structured document from individual job posting fields.
    Handles pandas Series, dicts, or raw string inputs.
    """
    if isinstance(item, str):
        return clean_text(item)

    title = clean_text(str(item.get("title", "") if pd.notnull(item.get("title", "")) else ""))
    company_profile = clean_text(str(item.get("company_profile", "") if pd.notnull(item.get("company_profile", "")) else ""))
    description = clean_text(str(item.get("description", "") if pd.notnull(item.get("description", "")) else ""))
    requirements = clean_text(str(item.get("requirements", "") if pd.notnull(item.get("requirements", "")) else ""))
    benefits = clean_text(str(item.get("benefits", "") if pd.notnull(item.get("benefits", "")) else ""))

    parts = []
    if title:
        parts.append(f"title: {title}")
    if company_profile:
        parts.append(f"company profile: {company_profile}")
    if description:
        parts.append(f"description: {description}")
    if requirements:
        parts.append(f"requirements: {requirements}")
    if benefits:
        parts.append(f"benefits: {benefits}")

    return " ".join(parts)


def extract_metadata_features(item: dict) -> dict:
    """
    Extract structured tabular risk signals from metadata fields.
    Works for single prediction dictionaries or pandas rows.
    """
    def to_binary(val):
        if val in [1, True, "1", "t", "T", "true", "True"]:
            return 1
        return 0

    has_logo = to_binary(item.get("has_company_logo", 0))
    has_questions = to_binary(item.get("has_questions", 0))
    telecommuting = to_binary(item.get("telecommuting", 0))

    comp_prof = str(item.get("company_profile", "") or "").strip()
    missing_company_profile = 1 if not comp_prof or comp_prof == "nan" else 0

    reqs = str(item.get("requirements", "") or "").strip()
    missing_requirements = 1 if not reqs or reqs == "nan" else 0

    bens = str(item.get("benefits", "") or "").strip()
    missing_benefits = 1 if not bens or bens == "nan" else 0

    return {
        "has_company_logo": has_logo,
        "has_questions": has_questions,
        "telecommuting": telecommuting,
        "missing_company_profile": missing_company_profile,
        "missing_requirements": missing_requirements,
        "missing_benefits": missing_benefits,
    }


def load_and_preprocess_dataset(csv_path: str = DATASET_PATH):
    """
    Load EMSCAD dataset, clean text fields, extract tabular features,
    and split into stratified Train (70%), Validation (15%), and Test (15%) sets.
    Explicitly drops internal `in_balanced_dataset` flag to avoid data leakage.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"EMSCAD dataset not found at {csv_path}")

    print(f"Loading EMSCAD from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Encode binary target: 't' -> 1 (fraud), 'f' -> 0 (legitimate)
    df["target"] = (df["fraudulent"].astype(str).str.lower() == "t").astype(int)

    # Drop internal leakage column if present
    if "in_balanced_dataset" in df.columns:
        df = df.drop(columns=["in_balanced_dataset"])

    print("Cleaning text and combining structured fields...")
    df["combined_text"] = df.apply(combine_job_text, axis=1)

    # Extract tabular metadata features
    print("Extracting tabular metadata indicators...")
    meta_df = pd.DataFrame(list(df.apply(extract_metadata_features, axis=1)))
    for col in meta_df.columns:
        df[col] = meta_df[col]

    df["text_length_log"] = np.log1p(df["combined_text"].str.len())

    # Stratified 70% Train, 15% Validation, 15% Test Split
    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        random_state=42,
        stratify=df["target"],
    )

    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=42,
        stratify=temp_df["target"],
    )

    print("\nDataset Partitioning Complete:")
    print(f"  Training Set:   {len(train_df):,} samples | Fraud: {train_df['target'].sum():,} ({train_df['target'].mean()*100:.2f}%)")
    print(f"  Validation Set: {len(val_df):,} samples | Fraud: {val_df['target'].sum():,} ({val_df['target'].mean()*100:.2f}%)")
    print(f"  Test Set:       {len(test_df):,} samples | Fraud: {test_df['target'].sum():,} ({test_df['target'].mean()*100:.2f}%)")

    return train_df, val_df, test_df


if __name__ == "__main__":
    train_df, val_df, test_df = load_and_preprocess_dataset()
    sample_text = "Urgent: Data entry operator needed. Earn Rs 50,000 monthly. No interview. Contact via Telegram."
    print("\nSample Text Cleaned:")
    print(clean_text(sample_text))
