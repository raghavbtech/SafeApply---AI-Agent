"""
SafeApply - Machine Learning Inference Layer
Loads the EMSCAD-trained classifier (17,880 job postings) to provide
probabilistic fraud risk scoring, confidence bands, and predictive token attribution.
"""

import os
import joblib
import numpy as np
from preprocessing import clean_text

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "safeapply_classifier.joblib")

_MODEL_CACHE = None


def load_classifier_artifact():
    """Load and cache the trained ML model artifact."""
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    if not os.path.exists(MODEL_PATH):
        return None

    try:
        _MODEL_CACHE = joblib.load(MODEL_PATH)
        return _MODEL_CACHE
    except Exception as exc:
        print(f"[ML Classifier Warning] Failed to load model from {MODEL_PATH}: {exc}")
        return None


def predict_job_offer(offer_text: str, metadata: dict = None) -> dict:
    """
    Evaluate job offer text using the EMSCAD ML classifier.

    Returns:
    - is_flagged: bool (whether probability exceeds optimal decision threshold)
    - ml_fraud_probability: float (0.0 to 1.0)
    - fraud_probability_pct: float (0 to 100)
    - risk_level: "High", "Medium", or "Low"
    - top_risk_tokens: list of detected predictive scam keywords
    - top_legit_tokens: list of detected corporate legitimacy keywords
    """
    if not offer_text or len(offer_text.strip()) < 10:
        return {
            "is_flagged": False,
            "ml_fraud_probability": 0.0,
            "fraud_probability_pct": 0.0,
            "risk_level": "Low",
            "verdict": "Insufficient Text",
            "top_risk_tokens": [],
            "top_legit_tokens": [],
            "model_version": "SafeApply-EMSCAD-v1.0",
        }

    artifact = load_classifier_artifact()
    if artifact is None:
        # Fallback simulation if model file is unavailable
        cleaned = clean_text(offer_text)
        high_risk_words = ["registration fee", "refundable", "upi", "telegram", "data entry", "earn", "cash", "no interview"]
        matches = [w for w in high_risk_words if w in cleaned]
        prob = min(0.15 + 0.25 * len(matches), 0.95) if matches else 0.05
        return {
            "is_flagged": prob >= 0.50,
            "ml_fraud_probability": round(prob, 4),
            "fraud_probability_pct": round(prob * 100, 1),
            "risk_level": "High" if prob >= 0.65 else ("Medium" if prob >= 0.30 else "Low"),
            "verdict": "Heuristic Mode",
            "top_risk_tokens": matches,
            "top_legit_tokens": [],
            "model_version": "Heuristic Fallback",
        }

    pipeline = artifact["pipeline"]
    threshold = artifact.get("optimal_threshold", 0.70)
    top_fraud_terms = artifact.get("top_fraud_terms", {})
    top_legit_terms = artifact.get("top_legit_terms", {})

    cleaned_text = clean_text(offer_text)

    try:
        prob = float(pipeline.predict_proba([cleaned_text])[0, 1])
    except Exception as e:
        print(f"[ML Classifier Error] Inference failed: {e}")
        prob = 0.5

    # Determine risk category based on calibrated thresholds
    if prob >= threshold:
        risk_level = "High"
        verdict = "Fraudulent Pattern Detected"
    elif prob >= 0.35:
        risk_level = "Medium"
        verdict = "Ambiguous Recruitment Signals"
    else:
        risk_level = "Low"
        verdict = "Standard Corporate Language"

    # Identify tokens present in text that drove the model's prediction
    matched_fraud = []
    for term, weight in top_fraud_terms.items():
        if term in cleaned_text and len(term) > 2:
            matched_fraud.append(term)
        if len(matched_fraud) >= 6:
            break

    matched_legit = []
    for term, weight in top_legit_terms.items():
        if term in cleaned_text and len(term) > 2:
            matched_legit.append(term)
        if len(matched_legit) >= 6:
            break

    return {
        "is_flagged": prob >= threshold,
        "ml_fraud_probability": round(prob, 4),
        "fraud_probability_pct": round(prob * 100, 1),
        "risk_level": risk_level,
        "verdict": verdict,
        "optimal_threshold": threshold,
        "top_risk_tokens": matched_fraud,
        "top_legit_tokens": matched_legit,
        "model_version": "SafeApply-EMSCAD-v1.0 (TF-IDF + Balanced LogReg)",
        "training_baseline": "17,880 real job postings (4.84% fraud baseline)",
    }


if __name__ == "__main__":
    sample_scam = """
    URGENT HIRING: Work from Home 2 hours daily doing copy paste data entry.
    Earn Rs 75,000 per month cash payout. No interview needed. Contact via Telegram link.
    """
    res = predict_job_offer(sample_scam)
    print("Scam Test Result:")
    print(f"  Probability: {res['fraud_probability_pct']}% ({res['risk_level']})")
    print(f"  Verdict:     {res['verdict']}")
    print(f"  Risk Tokens: {res['top_risk_tokens']}")

    sample_legit = """
    We are seeking a Software Engineer Intern at Microsoft India.
    Our team builds cloud infrastructure and digital services for enterprise clients.
    Please review the formal job description and company profile on our careers portal.
    """
    res2 = predict_job_offer(sample_legit)
    print("\nLegitimate Test Result:")
    print(f"  Probability: {res2['fraud_probability_pct']}% ({res2['risk_level']})")
    print(f"  Verdict:     {res2['verdict']}")
    print(f"  Legit Tokens:{res2['top_legit_tokens']}")
