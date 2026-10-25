"""New module API blueprints, registered on the existing Flask app."""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from api.ui import ui_bp
    from api.auth import auth_bp
    from api.cameras import cameras_bp
    from api.audit import audit_bp
    from api.visitors import visitors_bp
    from api.events import events_bp
    from api.alerts import alerts_bp
    from api.search import search_bp
    from api.analytics import analytics_bp
    from api.sensors import sensors_bp
    from api.registration import registration_bp

    app.register_blueprint(ui_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cameras_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(sensors_bp)
    app.register_blueprint(registration_bp)
