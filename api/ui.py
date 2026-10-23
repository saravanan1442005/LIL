"""UI shell routes: login/about views and page partials (no build step, Tailwind via CDN)."""
import os

from flask import Blueprint, abort, jsonify, render_template

import branding

ui_bp = Blueprint("ui", __name__)

# Whitelist prevents path traversal via /partials/<name>.
PARTIALS = {
    "visitor_overview",
    "live_monitoring",
    "visitors",
    "events",
    "alerts",
    "search_timeline",
    "cameras_zones",
    "analytics",
    "settings",
    "audit",
}


def _ctx():
    return {
        "product": branding.PRODUCT_NAME,
        "slogan": branding.SLOGAN,
        "version": branding.VERSION,
        "primary_module": branding.PRIMARY_MODULE,
        "legacy_module": branding.LEGACY_MODULE,
    }


@ui_bp.route("/login")
def login_view():
    return render_template("login.html", **_ctx())


@ui_bp.route("/about")
def about_view():
    return render_template("about.html", **_ctx())


@ui_bp.route("/partials/<name>")
def partial(name):
    if name not in PARTIALS:
        abort(404)
    return render_template(f"partials/{name}.html", **_ctx())


@ui_bp.route("/api/v2/meta")
def meta():
    return jsonify(
        {
            "product": branding.PRODUCT_NAME,
            "version": branding.VERSION,
            "slogan": branding.SLOGAN,
            "primary_module": branding.PRIMARY_MODULE,
            "legacy_module": branding.LEGACY_MODULE,
            "face_recognition_enabled": os.getenv("FACE_RECOGNITION_ENABLED", "false").lower() == "true",
        }
    )
