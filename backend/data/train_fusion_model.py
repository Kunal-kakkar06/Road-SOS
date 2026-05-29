"""
train_fusion_model.py — Train XGBoost fusion model for AI triage.

Run from the backend directory:
    python data/train_fusion_model.py

NOTE: The model file (models/fusion_triage.pkl) already exists if it was
previously trained. Re-running will overwrite it.

Generates synthetic multi-signal data where signal scores correlate
with ground-truth severity (P1–P4). In production, replace with real
triage records linking actual image/nlp/sensor scores to confirmed outcomes.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


FEATURE_NAMES = [
    "image_score", "nlp_score", "sensor_score", "medical_risk",
    "has_image",   "has_nlp",   "has_sensor",
    "mean_signal", "max_signal", "signal_count",
]


def generate_data(n: int = 4000):
    import numpy as np
    import pandas as pd

    np.random.seed(42)
    rows = []
    for _ in range(n):
        has_img = np.random.random() > 0.30
        has_nlp = np.random.random() > 0.40
        has_sen = np.random.random() > 0.20

        # Ground truth: 15% P1, 30% P2, 35% P3, 20% P4
        true_sev = np.random.choice([0, 1, 2, 3], p=[0.15, 0.30, 0.35, 0.20])
        base     = 1.0 - true_sev * 0.22          # higher base = more severe signal

        img = float(np.clip(base + np.random.normal(0, 0.15), 0, 1)) if has_img else 0.5
        nlp = float(np.clip(base + np.random.normal(0, 0.18), 0, 1)) if has_nlp else 0.5
        sen = float(np.clip(base + np.random.normal(0, 0.12), 0, 1)) if has_sen else 0.5
        med = float(np.clip(0.5 + np.random.normal(0, 0.10), 0, 1))

        rows.append({
            "image_score":  img,
            "nlp_score":    nlp,
            "sensor_score": sen,
            "medical_risk": med,
            "has_image":    float(has_img),
            "has_nlp":      float(has_nlp),
            "has_sensor":   float(has_sen),
            "mean_signal":  (img + nlp + sen) / 3,
            "max_signal":   max(img, nlp, sen),
            "signal_count": float(has_img) + float(has_nlp) + float(has_sen),
            "label":        true_sev,
        })
    return pd.DataFrame(rows)


def train():
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    import joblib

    print("=" * 60)
    print("Training XGBoost fusion model for AI triage")
    print("Classes: 0=P1 Critical, 1=P2 Serious, 2=P3 Moderate, 3=P4 Minor")
    print("=" * 60)

    df  = generate_data(n=4000)
    X   = df[FEATURE_NAMES]
    y   = df["label"]

    print(f"\nDataset: {len(df)} samples")
    print("Class distribution:")
    for cls, cnt in y.value_counts().sort_index().items():
        names = ["P1 Critical", "P2 Serious", "P3 Moderate", "P4 Minor"]
        print(f"  {names[cls]}: {cnt} ({100*cnt/len(y):.1f}%)")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.10,
        subsample=0.80,
        colsample_bytree=0.80,
        eval_metric="mlogloss",
        random_state=42,
        verbosity=0,
    )

    print("\nFitting XGBoost...")
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_te, y_te)],
        verbose=False,
    )

    preds = model.predict(X_te)
    print("\nClassification report on test set:")
    print(classification_report(
        y_te, preds,
        target_names=["P1 Critical", "P2 Serious", "P3 Moderate", "P4 Minor"]
    ))

    os.makedirs("models", exist_ok=True)
    out_path = "models/fusion_triage.pkl"
    joblib.dump(model, out_path)
    print(f"Saved → backend/{out_path}")
    print("fusion_triage.py will load this model on next server start.")


if __name__ == "__main__":
    train()
