"""Analytics blueprint (/api/v2/analytics).
Calculates premises traffic KPIs, visitor category breakdowns, peak activity hours, and dwell times.
"""
import datetime
from flask import Blueprint, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.connection import get_session_factory
from database.models import Visitor, Event, Alert, Camera

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v2/analytics")


@analytics_bp.route("/overview", methods=["GET"])
def get_analytics_overview():
    session: Session = get_session_factory()()
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total visitors
        total_visitors = session.query(Visitor).filter(Visitor.status != "MERGED").count()
        visits_today = session.query(Event).filter(Event.timestamp >= today_start).count()
        active_cameras = session.query(Camera).filter(Camera.enabled.is_(True)).count()
        active_alerts = session.query(Alert).filter(Alert.status == "NEW").count()

        # Category breakdown
        cat_counts = (
            session.query(Visitor.category, func.count(Visitor.id))
            .filter(Visitor.status != "MERGED")
            .group_by(Visitor.category)
            .all()
        )
        categories = {cat: count for cat, count in cat_counts}

        # Event type counts
        event_counts = (
            session.query(Event.event_type, func.count(Event.id))
            .group_by(Event.event_type)
            .all()
        )
        events_breakdown = {etype: count for etype, count in event_counts}

        # Top frequent visitors
        top_visitors = (
            session.query(Visitor)
            .filter(Visitor.status != "MERGED")
            .order_by(Visitor.total_visits.desc())
            .limit(5)
            .all()
        )

        return jsonify({
            "kpis": {
                "total_registered_visitors": total_visitors,
                "events_today": visits_today,
                "active_cameras": active_cameras,
                "unresolved_alerts": active_alerts,
            },
            "category_distribution": categories,
            "events_distribution": events_breakdown,
            "top_frequent_visitors": [v.to_dict() for v in top_visitors],
        })
    finally:
        session.close()
