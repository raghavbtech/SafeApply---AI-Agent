"""
SafeApply - Model Training & Evaluation Suite
Trains baseline and hybrid classifiers on the EMSCAD dataset,
tunes decision thresholds for severe class imbalance (4.84% fraud),
evaluates on validation & test sets, and serializes the best production model.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
    precision_recall_curve,
    roc_curve,
    f1_score,
    precision_score,
    recall_score,
)

from preprocessing import load_and_preprocess_dataset

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

TABULAR_FEATURES = [
    "has_company_logo",
    "has_questions",
    "telecommuting",
    "missing_company_profile",
    "missing_requirements",
    "missing_benefits",
    "text_length_log",
]


def train_and_evaluate():
    print("=" * 70)
    print("SAFEAPPLY EMSCAD MACHINE LEARNING BENCHMARK")
    print("=" * 70)

    # 1. Load Preprocessed & Stratified Splits
    train_df, val_df, test_df = load_and_preprocess_dataset()

    X_train_text = train_df["combined_text"]
    y_train = train_df["target"]

    X_val_text = val_df["combined_text"]
    y_val = val_df["target"]

    X_test_text = test_df["combined_text"]
    y_test = test_df["target"]

    # -----------------------------------------------------------------
    # EXPERIMENT 1: TF-IDF + Logistic Regression (Balanced Class Weight)
    # -----------------------------------------------------------------
    print("\n--- Training Model 1: TF-IDF + Logistic Regression (Balanced) ---")
    pipe_lr = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=10000, stop_words="english", ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, C=1.0, random_state=42)),
    ])
    pipe_lr.fit(X_train_text, y_train)

    val_probs_lr = pipe_lr.predict_proba(X_val_text)[:, 1]
    val_preds_lr = (val_probs_lr >= 0.5).astype(int)
    val_f1_lr = f1_score(y_val, val_preds_lr)
    val_rec_lr = recall_score(y_val, val_preds_lr)
    val_prec_lr = precision_score(y_val, val_preds_lr)
    val_roc_lr = roc_auc_score(y_val, val_probs_lr)
    val_pr_lr = average_precision_score(y_val, val_probs_lr)

    print(f"  Model 1 Val: F1={val_f1_lr:.4f} | Recall={val_rec_lr:.4f} | Precision={val_prec_lr:.4f} | PR-AUC={val_pr_lr:.4f} | ROC-AUC={val_roc_lr:.4f}")

    # -----------------------------------------------------------------
    # EXPERIMENT 2: TF-IDF + Complement Naive Bayes (Imbalance Aware)
    # -----------------------------------------------------------------
    print("\n--- Training Model 2: TF-IDF + Complement Naive Bayes ---")
    pipe_cnb = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=10000, stop_words="english", ngram_range=(1, 2), sublinear_tf=True)),
        ("clf", ComplementNB(alpha=0.5)),
    ])
    pipe_cnb.fit(X_train_text, y_train)

    val_probs_cnb = pipe_cnb.predict_proba(X_val_text)[:, 1]
    val_preds_cnb = (val_probs_cnb >= 0.5).astype(int)
    val_f1_cnb = f1_score(y_val, val_preds_cnb)
    val_rec_cnb = recall_score(y_val, val_preds_cnb)
    val_prec_cnb = precision_score(y_val, val_preds_cnb)
    val_roc_cnb = roc_auc_score(y_val, val_probs_cnb)
    val_pr_cnb = average_precision_score(y_val, val_probs_cnb)

    print(f"  Model 2 Val: F1={val_f1_cnb:.4f} | Recall={val_rec_cnb:.4f} | Precision={val_prec_cnb:.4f} | PR-AUC={val_pr_cnb:.4f} | ROC-AUC={val_roc_cnb:.4f}")

    # -----------------------------------------------------------------
    # EXPERIMENT 3: Hybrid (TF-IDF Text + Tabular Metadata Signals)
    # -----------------------------------------------------------------
    print("\n--- Training Model 3: Hybrid ColumnTransformer (Text + Metadata) ---")
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(max_features=10000, stop_words="english", ngram_range=(1, 2), sublinear_tf=True), "combined_text"),
            ("meta", StandardScaler(), TABULAR_FEATURES),
        ]
    )

    feature_cols = ["combined_text"] + TABULAR_FEATURES
    X_train_full = train_df[feature_cols]
    X_val_full = val_df[feature_cols]
    X_test_full = test_df[feature_cols]

    pipe_hybrid = Pipeline([
        ("prep", preprocessor),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, C=1.5, random_state=42)),
    ])
    pipe_hybrid.fit(X_train_full, y_train)

    val_probs_hyb = pipe_hybrid.predict_proba(X_val_full)[:, 1]
    val_preds_hyb = (val_probs_hyb >= 0.5).astype(int)
    val_f1_hyb = f1_score(y_val, val_preds_hyb)
    val_rec_hyb = recall_score(y_val, val_preds_hyb)
    val_prec_hyb = precision_score(y_val, val_preds_hyb)
    val_roc_hyb = roc_auc_score(y_val, val_probs_hyb)
    val_pr_hyb = average_precision_score(y_val, val_probs_hyb)

    print(f"  Model 3 Val: F1={val_f1_hyb:.4f} | Recall={val_rec_hyb:.4f} | Precision={val_prec_hyb:.4f} | PR-AUC={val_pr_hyb:.4f} | ROC-AUC={val_roc_hyb:.4f}")

    # Select Best Architecture
    models = {
        "TF-IDF + LogisticRegression": (pipe_lr, val_probs_lr, val_f1_lr, False),
        "TF-IDF + ComplementNB": (pipe_cnb, val_probs_cnb, val_f1_cnb, False),
        "Hybrid (Text + Metadata) + LogReg": (pipe_hybrid, val_probs_hyb, val_f1_hyb, True),
    }

    best_name = max(models, key=lambda k: models[k][2])
    best_pipe, best_val_probs, best_val_f1, is_hybrid = models[best_name]
    print(f"\n>>> Selected Best Architecture on Validation: {best_name} (F1={best_val_f1:.4f})")

    # -----------------------------------------------------------------
    # DECISION THRESHOLD TUNING (on Validation Set)
    # -----------------------------------------------------------------
    print("\n--- Tuning Decision Threshold on Validation Set ---")
    best_thresh = 0.50
    best_thresh_f1 = 0.0
    thresholds = np.linspace(0.20, 0.85, 27)

    threshold_records = []
    for th in thresholds:
        preds = (best_val_probs >= th).astype(int)
        f1 = f1_score(y_val, preds, zero_division=0)
        rec = recall_score(y_val, preds, zero_division=0)
        prec = precision_score(y_val, preds, zero_division=0)
        threshold_records.append({"threshold": round(th, 3), "f1": f1, "recall": rec, "precision": prec})
        if f1 > best_thresh_f1:
            best_thresh_f1 = f1
            best_thresh = th

    print(f"Optimal Decision Threshold: {best_thresh:.3f} with Validation F1: {best_thresh_f1:.4f}")

    # -----------------------------------------------------------------
    # FINAL EVALUATION ON UNSEEN TEST SET (2,682 Postings)
    # -----------------------------------------------------------------
    print("\n" + "=" * 70)
    print("FINAL EVALUATION ON UNSEEN TEST SET (2,682 POSTINGS)")
    print("=" * 70)

    X_test_eval = X_test_full if is_hybrid else X_test_text
    test_probs = best_pipe.predict_proba(X_test_eval)[:, 1]
    test_preds = (test_probs >= best_thresh).astype(int)

    test_f1 = f1_score(y_test, test_preds)
    test_rec = recall_score(y_test, test_preds)
    test_prec = precision_score(y_test, test_preds)
    test_roc = roc_auc_score(y_test, test_probs)
    test_pr_auc = average_precision_score(y_test, test_probs)

    print(classification_report(y_test, test_preds, target_names=["Legitimate (0)", "Fraudulent (1)"], digits=4))
    print(f"Test Fraud F1-Score: {test_f1:.4f}")
    print(f"Test Fraud Recall:   {test_rec:.4f} ({int(test_rec * y_test.sum())}/{y_test.sum()} scams caught)")
    print(f"Test Fraud Precision:{test_prec:.4f}")
    print(f"Test PR-AUC:         {test_pr_auc:.4f}")
    print(f"Test ROC-AUC:        {test_roc:.4f}")

    # Confusion Matrix
    cm = confusion_matrix(y_test, test_preds)
    print(f"\nConfusion Matrix:\n{cm}")
    tn, fp, fn, tp = cm.ravel()
    print(f"  True Negatives (Legit verified): {tn}")
    print(f"  False Positives (False alarms):  {fp}")
    print(f"  False Negatives (Missed scams):  {fn}")
    print(f"  True Positives (Scams detected): {tp}")

    # Plot Confusion Matrix
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Legitimate", "Fraudulent"],
                yticklabels=["Legitimate", "Fraudulent"], ax=ax)
    ax.set_title(f"Test Confusion Matrix (Threshold={best_thresh:.2f})", fontweight="bold")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    plt.tight_layout()
    fig.savefig(os.path.join(MODEL_DIR, "confusion_matrix.png"), dpi=200)
    plt.close()

    # Plot Precision-Recall and ROC Curves
    prec_pts, rec_pts, _ = precision_recall_curve(y_test, test_probs)
    fpr_pts, tpr_pts, _ = roc_curve(y_test, test_probs)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    axes[0].plot(rec_pts, prec_pts, color="#ef4444", lw=2, label=f"PR curve (PR-AUC = {test_pr_auc:.3f})")
    axes[0].set_xlabel("Recall (Fraud Detected)")
    axes[0].set_ylabel("Precision")
    axes[0].set_title("Precision-Recall Curve (4.84% Imbalance)", fontweight="bold")
    axes[0].legend(loc="lower left")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(fpr_pts, tpr_pts, color="#3b82f6", lw=2, label=f"ROC curve (AUC = {test_roc:.3f})")
    axes[1].plot([0, 1], [0, 1], color="#94a3b8", linestyle="--")
    axes[1].set_xlabel("False Positive Rate")
    axes[1].set_ylabel("True Positive Rate (Recall)")
    axes[1].set_title("ROC Curve", fontweight="bold")
    axes[1].legend(loc="lower right")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(os.path.join(MODEL_DIR, "evaluation_curves.png"), dpi=200)
    plt.close()

    # Extract Top Predictive Features
    feature_importance = {}
    if is_hybrid:
        prep_step = best_pipe.named_steps["prep"]
        clf_step = best_pipe.named_steps["clf"]
        text_names = list(prep_step.named_transformers_["text"].get_feature_names_out())
        all_features = text_names + TABULAR_FEATURES
        coefs = clf_step.coef_[0]
        top_fraud_idx = np.argsort(coefs)[-30:][::-1]
        top_legit_idx = np.argsort(coefs)[:30]

        top_fraud_terms = [(all_features[i], float(coefs[i])) for i in top_fraud_idx]
        top_legit_terms = [(all_features[i], float(coefs[i])) for i in top_legit_idx]
        feature_importance = {
            "top_fraud_indicators": top_fraud_terms,
            "top_legit_indicators": top_legit_terms,
        }
    else:
        vec_step = best_pipe.named_steps["tfidf"]
        clf_step = best_pipe.named_steps["clf"]
        feature_names = vec_step.get_feature_names_out()
        coefs = clf_step.coef_[0]
        top_fraud_idx = np.argsort(coefs)[-30:][::-1]
        top_legit_idx = np.argsort(coefs)[:30]
        top_fraud_terms = [(feature_names[i], float(coefs[i])) for i in top_fraud_idx]
        top_legit_terms = [(feature_names[i], float(coefs[i])) for i in top_legit_idx]
        feature_importance = {
            "top_fraud_indicators": top_fraud_terms,
            "top_legit_indicators": top_legit_terms,
        }

    print("\nTop 10 Learned Fraud Indicators:")
    for term, wt in feature_importance["top_fraud_indicators"][:10]:
        print(f"  {term:<25}: +{wt:.3f}")

    print("\nTop 10 Learned Legitimacy Indicators:")
    for term, wt in feature_importance["top_legit_indicators"][:10]:
        print(f"  {term:<25}: {wt:.3f}")

    # Serialize Model Artifact
    model_save_path = os.path.join(MODEL_DIR, "safeapply_classifier.joblib")
    artifact_payload = {
        "pipeline": best_pipe,
        "is_hybrid": is_hybrid,
        "optimal_threshold": float(best_thresh),
        "tabular_features": TABULAR_FEATURES if is_hybrid else [],
        "top_fraud_terms": dict(feature_importance["top_fraud_indicators"][:100]),
        "top_legit_terms": dict(feature_importance["top_legit_indicators"][:100]),
    }
    joblib.dump(artifact_payload, model_save_path, compress=3)
    print(f"\nProduction model serialized to {model_save_path}")

    # Model Card & Metadata JSON
    model_card = {
        "model_name": "SafeApply-EMSCAD-Classifier",
        "version": "1.0.0",
        "dataset": "EMSCAD (17,880 postings, 4.84% positive class)",
        "architecture": best_name,
        "is_hybrid": is_hybrid,
        "optimal_threshold": round(float(best_thresh), 3),
        "validation_metrics": {
            "f1": round(val_f1_hyb if is_hybrid else val_f1_lr, 4),
            "recall": round(val_rec_hyb if is_hybrid else val_rec_lr, 4),
            "precision": round(val_prec_hyb if is_hybrid else val_prec_lr, 4),
            "roc_auc": round(val_roc_hyb if is_hybrid else val_roc_lr, 4),
            "pr_auc": round(val_pr_hyb if is_hybrid else val_pr_lr, 4),
        },
        "test_metrics": {
            "test_samples": len(test_df),
            "test_fraud_count": int(y_test.sum()),
            "f1": round(test_f1, 4),
            "recall": round(test_rec, 4),
            "precision": round(test_prec, 4),
            "pr_auc": round(test_pr_auc, 4),
            "roc_auc": round(test_roc, 4),
            "true_positives": int(tp),
            "false_negatives": int(fn),
            "false_positives": int(fp),
            "true_negatives": int(tn),
        },
        "top_fraud_indicators": [k for k, _ in feature_importance["top_fraud_indicators"][:20]],
        "top_legit_indicators": [k for k, _ in feature_importance["top_legit_indicators"][:20]],
    }

    card_path = os.path.join(MODEL_DIR, "model_card.json")
    with open(card_path, "w", encoding="utf-8") as f:
        json.dump(model_card, f, indent=2)
    print(f"Model card written to {card_path}")

    return model_card


if __name__ == "__main__":
    train_and_evaluate()
