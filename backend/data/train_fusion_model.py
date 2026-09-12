"""
train_fusion_model.py — Train XGBoost fusion model for AI triage.

Run from the backend directory:
    python data/train_fusion_model.py

Generates synthetic multi-signal data where signal scores correlate
with ground-truth severity (P1–P4). Produces a trained model and 
metadata.json.
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FEATURE_NAMES = [
    "image_score", "nlp_score", "sensor_score", "medical_risk",
    "has_image",   "has_nlp",   "has_sensor",
    "mean_signal", "max_signal", "signal_count",
]
CLASS_NAMES = ["CRITICAL", "HIGH", "MODERATE", "LOW"]

def generate_data(n: int = 5000, seed: int = 42):
    import numpy as np
    import pandas as pd

    np.random.seed(seed)
    rows = []
    for _ in range(n):
        # Determine signals available
        has_img = np.random.random() > 0.40
        has_nlp = np.random.random() > 0.10
        has_sen = np.random.random() > 0.50
        
        # Ensure at least one signal is available
        if not (has_img or has_nlp or has_sen):
            has_nlp = True

        # Ground truth: balanced classes
        true_sev = np.random.choice([0, 1, 2, 3], p=[0.25, 0.25, 0.25, 0.25])
        
        # Base signal strength based on severity (0 is critical -> highest base)
        base = 1.0 - (true_sev * 0.25)
        
        img = float(np.clip(base + np.random.normal(0, 0.15), 0, 1)) if has_img else 0.5
        nlp = float(np.clip(base + np.random.normal(0, 0.15), 0, 1)) if has_nlp else 0.5
        sen = float(np.clip(base + np.random.normal(0, 0.15), 0, 1)) if has_sen else 0.5
        med = float(np.clip(0.5 + np.random.normal(0, 0.10), 0, 1))
        
        # To make it less trivial, occasionally add strong noise
        if np.random.random() < 0.05:
            nlp = float(np.clip(nlp - 0.4, 0, 1)) if has_nlp else 0.5
            
        mean_sig = (img + nlp + sen) / 3
        max_sig = max(img, nlp, sen)
        sig_count = float(has_img) + float(has_nlp) + float(has_sen)
        
        rows.append({
            "image_score":  img,
            "nlp_score":    nlp,
            "sensor_score": sen,
            "medical_risk": med,
            "has_image":    float(has_img),
            "has_nlp":      float(has_nlp),
            "has_sensor":   float(has_sen),
            "mean_signal":  mean_sig,
            "max_signal":   max_sig,
            "signal_count": sig_count,
            "label":        true_sev,
        })
    return pd.DataFrame(rows)


def train():
    from xgboost import XGBClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix
    import joblib

    print("=" * 60)
    print("Training XGBoost fusion model for AI triage")
    print("=" * 60)

    dataset_size = 5000
    random_seed = 42
    df = generate_data(n=dataset_size, seed=random_seed)
    X = df[FEATURE_NAMES]
    y = df["label"]

    print(f"\nDataset: {len(df)} samples (SYNTHETIC)")
    print("Class distribution:")
    for cls, cnt in y.value_counts().sort_index().items():
        print(f"  {CLASS_NAMES[cls]}: {cnt} ({100*cnt/len(y):.1f}%)")

    # 70/15/15 split
    X_tr_val, X_te, y_tr_val, y_te = train_test_split(
        X, y, test_size=0.15, random_state=random_seed, stratify=y
    )
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_tr_val, y_tr_val, test_size=(0.15/0.85), random_state=random_seed, stratify=y_tr_val
    )

    print(f"\nSplits:")
    print(f"  Train:      {len(X_tr)} ({(len(X_tr)/len(df))*100:.1f}%)")
    print(f"  Validation: {len(X_val)} ({(len(X_val)/len(df))*100:.1f}%)")
    print(f"  Test:       {len(X_te)} ({(len(X_te)/len(df))*100:.1f}%)")

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.10,
        subsample=0.80,
        colsample_bytree=0.80,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=random_seed,
        verbosity=0,
    )

    print("\nFitting XGBoost...")
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # Evaluation on strictly held-out test set
    preds = model.predict(X_te)
    
    acc = accuracy_score(y_te, preds)
    macro_f1 = f1_score(y_te, preds, average='macro')
    weighted_f1 = f1_score(y_te, preds, average='weighted')
    cm = confusion_matrix(y_te, preds)

    print("\n--- MODEL EVALUATION (Test Set) ---")
    print(f"Accuracy:    {acc:.4f}")
    print(f"Macro F1:    {macro_f1:.4f}")
    print(f"Weighted F1: {weighted_f1:.4f}")
    
    print("\nConfusion Matrix:")
    print(cm)
    
    print("\nDetailed Report:")
    print(classification_report(y_te, preds, target_names=CLASS_NAMES))

    os.makedirs("models", exist_ok=True)
    out_path = "models/fusion_triage.pkl"
    meta_path = "models/metadata.json"
    
    joblib.dump(model, out_path)
    print(f"\nSaved Model → backend/{out_path}")
    
    metadata = {
        "model_version": "1.1.0",
        "feature_version": "1.0",
        "training_dataset_type": "synthetic",
        "training_sample_count": dataset_size,
        "training_random_seed": random_seed,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_names": FEATURE_NAMES,
        "class_names": CLASS_NAMES,
        "metrics": {
            "test_accuracy": acc,
            "test_macro_f1": macro_f1,
            "test_weighted_f1": weighted_f1
        }
    }
    
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved Metadata → backend/{meta_path}")

if __name__ == "__main__":
    train()
