# RoadSOS Production ML Performance & Model Drift Monitoring Policy

**Policy Version**: v1.0.0  
**Target Engine**: XGBoost 2.0 + NLP TF-IDF + SHAP Explainability Engine  
**Model Checksum**: `e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1` (SHA-256)

---

## 1. Production ML Monitoring Dimensions

| ML Monitoring Dimension | Tracked Metric / Distribution | Expected Range | Anomaly Action |
| :--- | :--- | :---: | :--- |
| **Severity Distribution** | `P1` Critical, `P2` Serious, `P3` Moderate, `P4` Minor | P1: 10-15%, P2: 20-30%, P3: 30-40%, P4: 25-35% | Trigger feature drift audit |
| **Confidence Scores** | Mean ML Probability Score | `0.65 - 0.95` | Alert if mean confidence < 0.50 |
| **SHAP Factor Stability** | Top feature attributions (`speed_at_crash`, `head_injury_risk`) | Consistent feature ranking | Audit input data quality |
| **Model Checksum** | `fusion_triage.pkl` SHA-256 hash | `e014884ed8...` | **BLOCK RELEASE** if mismatch |

---

## 2. Model Drift Detection & Retraining Boundary

- **Feature Drift Threshold**: Kolmogorov-Smirnov (KS) test p-value < 0.05 on feature distributions.
- **Retraining Invariant**: Zero manual weight edits allowed in production. Retraining MUST follow strict release management SOP (Step 33).
