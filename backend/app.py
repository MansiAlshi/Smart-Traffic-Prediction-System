import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask
from backend.config import Config
from backend.extensions import mysql
from backend.api.auth_api import auth_bp
from backend.api.prediction_api import prediction_bp
from backend.api.route_api import route_bp
from backend.api.analytics_api import analytics_bp
from backend.api.pages import pages_bp


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(Config.BASE_DIR, 'templates'),
        static_folder=os.path.join(Config.BASE_DIR, 'static'),
    )
    app.config.from_object(Config)

    mysql.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(route_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(pages_bp)

    @app.errorhandler(404)
    def not_found(e):
        return {'success': False, 'message': 'Resource not found'}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {'success': False, 'message': 'Internal server error'}, 500

    # Pre-load ML model to prevent lazy-loading delay on the first API request
    try:
        from backend.ml.predictor import TrafficPredictor
        TrafficPredictor().load()
    except Exception as e:
        app.logger.warning(f"Failed to pre-load ML model at startup: {e}")

    return app
