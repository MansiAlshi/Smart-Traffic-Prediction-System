"""
Data preprocessing pipeline for traffic congestion prediction.
Supports Indian Road Accident Dataset (2022-2025) from Kaggle.
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
import xgboost as xgb
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'traffic_dataset.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'traffic_model.joblib')
ENCODER_PATH = os.path.join(MODEL_DIR, 'encoders.joblib')
METRICS_PATH = os.path.join(MODEL_DIR, 'metrics.json')
FEATURE_IMPORTANCE_PATH = os.path.join(MODEL_DIR, 'feature_importance.json')

FEATURE_COLUMNS = [
    'city', 'weather_condition', 'temperature', 'visibility',
    'festival_indicator', 'peak_hour_indicator', 'road_type',
    'num_lanes', 'traffic_density', 'hour', 'day', 'month',
    'is_weekend', 'weather_severity', 'festival_impact'
]

TARGET_COLUMN = 'congestion_level'


def load_and_clean(filepath=None):
    filepath = filepath or DATA_PATH
    if not os.path.exists(filepath):
        from generate_data import main as gen_main
        gen_main()
    df = pd.read_csv(filepath)

    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    column_map = {
        'weather_conditions': 'weather_condition',
        'weather': 'weather_condition',
        'congestion': 'congestion_level',
        'traffic_level': 'congestion_level',
        'lanes': 'num_lanes',
        'number_of_lanes': 'num_lanes',
    }
    df.rename(columns=column_map, inplace=True)

    if 'congestion_level' not in df.columns and 'accident_severity' in df.columns:
        severity_map = {1: 'Low', 2: 'Medium', 3: 'High', 'Slight': 'Low',
                        'Serious': 'Medium', 'Fatal': 'High'}
        df['congestion_level'] = df['accident_severity'].map(severity_map).fillna('Medium')

    if 'date' in df.columns and 'hour' not in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['hour'] = df['date'].dt.hour
        df['day'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['is_weekend'] = (df['date'].dt.dayofweek >= 5).astype(int)

    if 'time' in df.columns and 'hour' not in df.columns:
        df['hour'] = pd.to_datetime(df['time'], format='%H:%M', errors='coerce').dt.hour

    df.drop_duplicates(inplace=True)

    for col in ['temperature', 'visibility', 'traffic_density', 'num_lanes']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col].fillna(df[col].median(), inplace=True)

    categorical_defaults = {
        'city': 'Mumbai',
        'weather_condition': 'Clear',
        'road_type': 'Urban',
    }
    for col, default in categorical_defaults.items():
        if col in df.columns:
            df[col].fillna(default, inplace=True)

    for col in ['festival_indicator', 'peak_hour_indicator', 'is_weekend']:
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    if 'weather_severity' not in df.columns and 'weather_condition' in df.columns:
        severity_map = {'Clear': 0.1, 'Cloudy': 0.3, 'Haze': 0.4, 'Fog': 0.6, 'Rain': 0.7, 'Storm': 0.9}
        df['weather_severity'] = df['weather_condition'].map(severity_map).fillna(0.3)

    if 'festival_impact' not in df.columns:
        df['festival_impact'] = df['festival_indicator'].apply(lambda x: 0.8 if x else 0.0)

    if 'hour' not in df.columns:
        df['hour'] = 12
    if 'day' not in df.columns:
        df['day'] = 15
    if 'month' not in df.columns:
        df['month'] = 6
    if 'is_weekend' not in df.columns:
        df['is_weekend'] = 0

    if TARGET_COLUMN in df.columns:
        df[TARGET_COLUMN] = df[TARGET_COLUMN].str.strip().str.title()
        valid = {'Low', 'Medium', 'High'}
        df = df[df[TARGET_COLUMN].isin(valid)]

    return df


def encode_features(df, encoders=None, fit=True):
    encoders = encoders or {}
    encoded = df.copy()
    cat_cols = ['city', 'weather_condition', 'road_type']

    for col in cat_cols:
        if col not in encoded.columns:
            continue
        if fit:
            le = LabelEncoder()
            encoded[col] = le.fit_transform(encoded[col].astype(str))
            encoders[col] = le
        else:
            le = encoders[col]
            known = set(le.classes_)
            encoded[col] = encoded[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in known else le.transform([le.classes_[0]])[0]
            )

    numeric_cols = [
        'temperature', 'visibility', 'festival_indicator', 'peak_hour_indicator',
        'num_lanes', 'traffic_density', 'hour', 'day', 'month',
        'is_weekend', 'weather_severity', 'festival_impact'
    ]
    for col in numeric_cols:
        if col not in encoded.columns:
            encoded[col] = 0

    feature_cols = cat_cols + numeric_cols
    available = [c for c in feature_cols if c in encoded.columns]
    return encoded[available], encoders, available


def train_model(filepath=None):
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = load_and_clean(filepath)
    print(f'Dataset shape after cleaning: {df.shape}')

    X_raw, encoders, feature_names = encode_features(df[FEATURE_COLUMNS], fit=True)
    y_raw = df[TARGET_COLUMN]

    target_encoder = LabelEncoder()
    y = target_encoder.fit_transform(y_raw)
    encoders['target'] = target_encoder

    X_train, X_test, y_train, y_test = train_test_split(
        X_raw, y, test_size=0.2, random_state=42, stratify=y
    )

    param_grid = {
        'max_depth': [4, 6, 8],
        'learning_rate': [0.05, 0.1],
        'n_estimators': [100, 200],
        'subsample': [0.8, 1.0],
    }

    base_model = xgb.XGBClassifier(
        objective='multi:softprob',
        eval_metric='mlogloss',
        random_state=42,
    )

    print('Running hyperparameter tuning...')
    grid = GridSearchCV(
        base_model, param_grid, cv=3, scoring='f1_weighted', n_jobs=-1, verbose=1
    )
    grid.fit(X_train, y_train)
    best_model = grid.best_estimator_
    print(f'Best params: {grid.best_params_}')

    y_pred = best_model.predict(X_test)
    y_proba = best_model.predict_proba(X_test)

    labels = target_encoder.classes_
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
        'recall': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
        'f1_score': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
        'classification_report': classification_report(y_test, y_pred, target_names=labels, output_dict=True),
        'best_params': grid.best_params_,
        'feature_names': feature_names,
        'classes': labels.tolist(),
    }

    importance = dict(zip(feature_names, best_model.feature_importances_.tolist()))
    metrics['feature_importance'] = importance

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump({'encoders': encoders, 'feature_names': feature_names}, ENCODER_PATH)

    with open(METRICS_PATH, 'w') as f:
        json.dump(metrics, f, indent=2)
    with open(FEATURE_IMPORTANCE_PATH, 'w') as f:
        json.dump(importance, f, indent=2)

    print('\n=== Model Evaluation ===')
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1_score']:.4f}")
    print(f"Confusion Matrix:\n{np.array(metrics['confusion_matrix'])}")
    print(f'\nModel saved to {MODEL_PATH}')
    return best_model, metrics


if __name__ == '__main__':
    train_model()
