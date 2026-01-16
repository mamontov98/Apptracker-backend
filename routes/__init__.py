from flask import Blueprint
from .health import health_bp
from .db import db_bp
from .events import events_bp
from .projects import projects_bp
from .reports import reports_bp

def register_routes(app):
    """Register all route blueprints"""
    app.register_blueprint(health_bp)
    app.register_blueprint(db_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(reports_bp)

