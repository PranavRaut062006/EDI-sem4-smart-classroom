"""
Flask application factory.
"""

from flask import Flask
from flask_cors import CORS
from config import Config
from app.models.database import init_db
from app.routes.students import students_bp
from app.routes.attendance import attendance_bp
from app.routes.analytics import analytics_bp
from app.routes.iot import iot_bp


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS(app, origins=config_class.CORS_ORIGINS)

    # ── Database ──────────────────────────────────────────────────────────────
    init_db(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(students_bp,    url_prefix="/api/students")
    app.register_blueprint(attendance_bp,  url_prefix="/api/attendance")
    app.register_blueprint(analytics_bp,   url_prefix="/api/analytics")
    app.register_blueprint(iot_bp,         url_prefix="/api/iot")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    return app
