import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'smart_traffic_db')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_SSL = os.getenv('MYSQL_SSL', 'false').lower() == 'true'

    MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'models', 'traffic_model.joblib')
    ENCODER_PATH = os.path.join(BASE_DIR, 'ml', 'models', 'encoders.joblib')
    METRICS_PATH = os.path.join(BASE_DIR, 'ml', 'models', 'metrics.json')
    DATA_PATH = os.path.join(BASE_DIR, 'ml', 'data', 'traffic_dataset.csv')

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400
