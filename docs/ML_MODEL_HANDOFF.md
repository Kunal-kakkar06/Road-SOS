# RoadSOS Machine Learning Pipeline & Model Handoff Guide

**Target Audience**: ML Engineers, Data Scientists, AI Researchers  
**Release Version**: RoadSOS v1.0.0 ML Release Candidate  
**Artifact File**: `backend/models/fusion_triage.pkl`  
**Model Checksum**: `e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1` (SHA-256)

---

## 1. ML Model Architecture & Feature Engineering

RoadSOS utilizes a high-performance XGBoost Classifier fused with NLP TF-IDF text scoring and SHAP TreeExplainer feature attribution.

### 10-Feature Vector Ordering (Strict Invariant)

The input vector passed to XGBoost `predict_proba()` strictly follows this 10-feature order:

| Index | Feature Name | Description | Data Type | Range / Encoding |
| :---: | :--- | :--- | :---: | :---: |
| `0` | `speed_at_crash` | Vehicle impact speed (km/h) | float | `0.0 - 250.0` |
| `1` | `g_force` | Sensor accelerometer peak g-force | float | `0.0 - 50.0` |
| `2` | `airbag_deployed` | Airbag deployment status | int | `0` (No) or `1` (Yes) |
| `3` | `rollover` | Vehicle rollover status | int | `0` (No) or `1` (Yes) |
| `4` | `head_injury_risk` | Head trauma risk score from vision/NLP | float | `0.0 - 1.0` |
| `5` | `severe_bleeding_flag` | Severe hemorrhage indicator | int | `0` (No) or `1` (Yes) |
| `6` | `unconscious_flag` | Victim unresponsiveness indicator | int | `0` (No) or `1` (Yes) |
| `7` | `trapped_flag` | Vehicle entrapment indicator | int | `0` (No) or `1` (Yes) |
| `8` | `nlp_severity_score` | TF-IDF + Keyword emergency score | float | `0.0 - 1.0` |
| `9` | `multi_vehicle_flag` | Multi-vehicle collision indicator | int | `0` (No) or `1` (Yes) |

---

## 2. SHAP Explainability & Inference Contract

- **SHAP Computation**: Computed via `shap.TreeExplainer(model)` returning positive and negative feature attribution weights.
- **Severity Mapping**:
  - `P1 (Critical)`: Score >= `0.75`
  - `P2 (Serious)`: Score >= `0.50` and < `0.75`
  - `P3 (Moderate)`: Score >= `0.25` and < `0.50`
  - `P4 (Minor)`: Score < `0.25`

---

## 3. Strict Rules for Future Model Updates

If retraining or replacing `fusion_triage.pkl` in future releases:
1. **Feature Vector Order**: Maintain the exact 10-feature ordering without changing indices.
2. **Checksum Verification**: Re-calculate SHA-256 hash of new model file and update `RELEASE_ARTIFACT_MANIFEST.md`.
3. **Regression Suite**: Must pass all 300 backend regression tests with 100% pass rate.
4. **Fallback Mechanism**: Maintain XGBoost fallback rules in `base_model.py` if model file fails to load.
