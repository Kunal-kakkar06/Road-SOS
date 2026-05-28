import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib, os


def generate_data(n=5000):
    np.random.seed(42)
    rows = []
    for _ in range(n):
        crash = np.random.random() < 0.3
        if crash:
            rows.append({
                'peak_acceleration':  np.random.uniform(15, 60),
                'delta_v':            np.random.uniform(20, 80),
                'jerk':               np.random.uniform(30, 120),
                'rotation_rate':      np.random.uniform(50, 300),
                'impact_duration_ms': np.random.uniform(50, 300),
                'pre_event_accel':    np.random.uniform(0, 5),
                'label': 1,
            })
        else:
            rows.append({
                'peak_acceleration':  np.random.uniform(0, 12),
                'delta_v':            np.random.uniform(0, 15),
                'jerk':               np.random.uniform(0, 25),
                'rotation_rate':      np.random.uniform(0, 40),
                'impact_duration_ms': np.random.uniform(10, 1000),
                'pre_event_accel':    np.random.uniform(0, 8),
                'label': 0,
            })
    return pd.DataFrame(rows)


def train():
    df = generate_data()
    feats = ['peak_acceleration','delta_v','jerk',
             'rotation_rate','impact_duration_ms','pre_event_accel']
    X, y = df[feats], df['label']
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                               random_state=42, stratify=y)
    model = XGBClassifier(n_estimators=200, max_depth=5,
                           learning_rate=0.1, random_state=42,
                           eval_metric='logloss')
    model.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    print(classification_report(y_te, model.predict(X_te),
          target_names=['Normal','Crash']))
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, 'models/crash_classifier.pkl')
    print("Model saved → backend/models/crash_classifier.pkl")

if __name__ == '__main__':
    train()
