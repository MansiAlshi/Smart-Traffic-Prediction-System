# AI-Based Smart Traffic Prediction and Route Recommendation System

IEEE Internship Project — Smart Cities and Urban Innovation

## Overview

Full-stack web application that predicts traffic congestion using XGBoost ML, recommends optimal routes, and provides interactive traffic analytics with weather, festival, and peak-hour impact analysis.

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js, Leaflet Maps |
| Backend | Python, Flask |
| Database | MySQL |
| ML | XGBoost, Scikit-learn, Pandas, NumPy, Joblib |

## Project Structure

```
mmtt/
├── backend/           # Flask application, APIs, services, ML integration
├── ml/                # Data preprocessing, model training, saved models
├── database/          # MySQL schema and initialization scripts
├── templates/         # HTML templates (Jinja2)
├── static/            # CSS, JavaScript assets
├── run.py             # Application entry point
└── requirements.txt
```

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- MySQL 8.0+

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update MySQL credentials:

```bash
copy .env.example .env
```

### 4. Initialize Database

```bash
python database/init_db.py
```

Or manually run `database/schema.sql` in MySQL Workbench.

### 5. Train ML Model

```bash
python ml/train_model.py
```

Place the Kaggle dataset CSV at `ml/data/traffic_dataset.csv` to train on real data. Otherwise, a synthetic dataset is auto-generated based on the Indian Road Accident Dataset structure.

### 6. Run Application

```bash
python run.py
```

Open **http://localhost:5000**

Default login: `user` / `password123`

## Features

- User authentication (register, login, logout, session management)
- Traffic congestion prediction (Low / Medium / High) with confidence scores
- Route recommendation (3 routes with risk analysis)
- Interactive dashboard with Chart.js analytics
- Traffic heatmap with Leaflet Maps
- Travel history and saved routes
- Smart travel suggestions
- Weather, festival, and peak-hour impact analysis

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login |
| POST | `/api/auth/logout` | User logout |
| GET/PUT | `/api/auth/profile` | Profile management |
| POST | `/api/predict` | Traffic prediction |
| GET | `/api/predict/history` | Prediction history |
| POST | `/api/route/recommend` | Route recommendation |
| GET | `/api/route/history` | Travel history |
| POST | `/api/route/save` | Save route |
| GET | `/api/route/saved` | List saved routes |
| GET | `/api/analytics/dashboard` | Dashboard stats |
| GET | `/api/analytics/traffic` | Traffic analytics |
| GET | `/api/analytics/heatmap` | Heatmap data |
| POST | `/api/analytics/feedback` | Submit feedback |

## ML Pipeline

1. Data cleaning, duplicate removal, missing value handling
2. Feature engineering (hour, day, month, weekend, peak-hour, weather severity, festival impact)
3. Label encoding for categorical features
4. 80:20 train-test split
5. XGBoost with GridSearchCV hyperparameter tuning
6. Evaluation: Accuracy, Precision, Recall, F1, Confusion Matrix
7. Model saved via Joblib

## Limitations

- Predictions are based on historical data patterns
- No live traffic API integration
- Route recommendations use predicted (not real-time) conditions
- Results depend on dataset quality

## License

Academic project for IEEE internship demonstration.
