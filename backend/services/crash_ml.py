import joblib, numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / 'models' / 'crash_classifier.pkl'
_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model

def predict_crash(peak_acceleration, delta_v, jerk,
                  rotation_rate, impact_duration_ms, pre_event_accel):
    prob = float(get_model().predict_proba(
        np.array([[peak_acceleration, delta_v, jerk,
                   rotation_rate, impact_duration_ms, pre_event_accel]])
    )[0][1])

    if   prob >= 0.85: sev, label = 'P1', 'Critical — high-speed impact'
    elif prob >= 0.65: sev, label = 'P2', 'Serious — significant impact'
    elif prob >= 0.40: sev, label = 'P3', 'Moderate — possible collision'
    else:              sev, label = 'P4', 'Low — minor event'

    return {
        'crash_probability': round(prob, 4),
        'is_crash':          prob >= 0.40,
        'severity':          sev,
        'severity_label':    label,
    }
