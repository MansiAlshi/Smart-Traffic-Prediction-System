import os
import json
import numpy as np
import joblib
from backend.config import Config


class TrafficPredictor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        if not os.path.exists(Config.MODEL_PATH):
            from ml.preprocess import train_model
            train_model()
        self.model = joblib.load(Config.MODEL_PATH)
        saved = joblib.load(Config.ENCODER_PATH)
        self.encoders = saved['encoders']
        self.feature_names = saved['feature_names']
        self.target_encoder = self.encoders['target']
        self.metrics = {}
        if os.path.exists(Config.METRICS_PATH):
            with open(Config.METRICS_PATH) as f:
                self.metrics = json.load(f)
        self._loaded = True

    def _encode_row(self, data):
        row = {}
        cat_cols = ['city', 'weather_condition', 'road_type']
        for col in cat_cols:
            le = self.encoders[col]
            val = str(data.get(col, le.classes_[0]))
            if val not in le.classes_:
                val = le.classes_[0]
            row[col] = le.transform([val])[0]

        numeric_defaults = {
            'temperature': 28.0, 'visibility': 8.0, 'festival_indicator': 0,
            'peak_hour_indicator': 0, 'num_lanes': 2, 'traffic_density': 50.0,
            'hour': 12, 'day': 15, 'month': 6, 'is_weekend': 0,
            'weather_severity': 0.3, 'festival_impact': 0.0,
        }
        weather_severity_map = {
            'Clear': 0.1, 'Cloudy': 0.3, 'Haze': 0.4,
            'Fog': 0.6, 'Rain': 0.7, 'Storm': 0.9
        }

        for key, default in numeric_defaults.items():
            row[key] = float(data.get(key, default))

        if 'weather_severity' not in data:
            row['weather_severity'] = weather_severity_map.get(
                data.get('weather_condition', 'Clear'), 0.3
            )
        if 'festival_impact' not in data:
            row['festival_impact'] = 0.8 if int(data.get('festival_indicator', 0)) else 0.0

        return np.array([[row[f] for f in self.feature_names]])

    def predict(self, data):
        self.load()
        X = self._encode_row(data)
        proba = self.model.predict_proba(X)[0]
        pred_idx = int(np.argmax(proba))
        label = self.target_encoder.inverse_transform([pred_idx])[0]
        confidence = float(proba[pred_idx])
        risk = self._compute_risk(label, data, confidence)
        return {
            'predicted_congestion': label,
            'confidence_score': round(confidence, 4),
            'probabilities': {
                cls: round(float(p), 4)
                for cls, p in zip(self.target_encoder.classes_, proba)
            },
            'traffic_risk': risk,
        }

    def _compute_risk(self, congestion, data, confidence):
        risk_score = {'Low': 0.2, 'Medium': 0.5, 'High': 0.85}.get(congestion, 0.5)
        if data.get('weather_condition') in ('Rain', 'Storm', 'Fog'):
            risk_score += 0.1
        if int(data.get('peak_hour_indicator', 0)):
            risk_score += 0.08
        if float(data.get('visibility', 10)) < 3:
            risk_score += 0.1
        risk_score = min(1.0, risk_score)

        if risk_score < 0.35:
            return 'Low'
        if risk_score < 0.65:
            return 'Medium'
        return 'High'

    def get_feature_importance(self):
        self.load()
        return self.metrics.get('feature_importance', {})

    def get_metrics(self):
        self.load()
        return self.metrics
