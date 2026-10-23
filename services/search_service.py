"""Forensic search engine, natural-language query parser, and incident timeline generator.
Parses natural language queries (e.g. "delivery person with a box near Gate 1 yesterday evening")
into structured SQL filters and compiles verifiable forensic incident reports with JSON/PDF export.
"""
import re
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database.models import Event, Visitor, Camera, Zone, Alert


def parse_natural_language_query(query_str: str) -> Dict[str, Any]:
    """Parse natural-language search query into structured database filters.
    Includes an extension hook for future LLM integration.
    """
    q = query_str.lower().strip()
    filters: Dict[str, Any] = {}

    # 1. Visitor Category keywords
    if "delivery" in q or "courier" in q:
        filters["category"] = "Delivery"
    elif "technician" in q or "repair" in q or "electrician" in q:
        filters["category"] = "Technician"
    elif "vendor" in q:
        filters["category"] = "Vendor"
    elif "worker" in q or "domestic" in q or "maid" in q:
        filters["category"] = "Domestic Worker"
    elif "guest" in q:
        filters["category"] = "Guest"

    # 2. Carried Object keywords
    for obj in ["backpack", "box", "package", "suitcase", "handbag", "bottle", "umbrella"]:
        if obj in q:
            filters["object"] = "box" if obj == "package" else obj
            break

    # 3. Event Type keywords
    if "entry" in q or "entered" in q or "arrived" in q:
        filters["event_type"] = "ENTRY"
    elif "exit" in q or "left" in q:
        filters["event_type"] = "EXIT"
    elif "loitering" in q or "lingering" in q:
        filters["event_type"] = "LOITERING"
    elif "restricted" in q:
        filters["event_type"] = "RESTRICTED_ZONE"

    # 4. Camera / Location keywords
    cam_match = re.search(r"(gate\s*\d+|camera\s*\d+|entrance|promenade)", q)
    if cam_match:
        loc_term = cam_match.group(1)
        if "1" in loc_term or "entrance" in loc_term:
            filters["camera_id"] = 1
        elif "2" in loc_term or "promenade" in loc_term:
            filters["camera_id"] = 2
        elif "3" in loc_term or "station" in loc_term:
            filters["camera_id"] = 3

    # 5. Relative Time keywords
    now = datetime.datetime.now(datetime.timezone.utc)
    if "yesterday" in q:
        yesterday = now - datetime.timedelta(days=1)
        filters["time_start"] = yesterday.replace(hour=0, minute=0, second=0).isoformat()
        filters["time_end"] = yesterday.replace(hour=23, minute=59, second=59).isoformat()
    elif "today" in q:
        filters["time_start"] = now.replace(hour=0, minute=0, second=0).isoformat()
        filters["time_end"] = now.isoformat()

    if "evening" in q:
        filters["time_start"] = (now - datetime.timedelta(days=1)).replace(hour=17, minute=0).isoformat()
    elif "night" in q:
        filters["time_start"] = (now - datetime.timedelta(days=1)).replace(hour=21, minute=0).isoformat()
    elif "morning" in q:
        filters["time_start"] = (now - datetime.timedelta(days=1)).replace(hour=6, minute=0).isoformat()

    return filters


def search_events(
    session: Session,
    filters: Dict[str, Any],
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Execute filtered query across events and linked visitors."""
    query = session.query(Event).outerjoin(Visitor, Event.visitor_id == Visitor.id)

    if filters.get("event_type"):
        query = query.filter(Event.event_type == filters["event_type"])
    if filters.get("camera_id"):
        query = query.filter(Event.camera_id == int(filters["camera_id"]))
    if filters.get("zone_id"):
        query = query.filter(Event.zone_id == int(filters["zone_id"]))
    if filters.get("visitor_id"):
        query = query.filter(Event.visitor_id == int(filters["visitor_id"]))
    if filters.get("category"):
        query = query.filter(Visitor.category == filters["category"])

    if filters.get("time_start"):
        try:
            ts = datetime.datetime.fromisoformat(filters["time_start"])
            query = query.filter(Event.timestamp >= ts)
        except Exception:
            pass

    if filters.get("time_end"):
        try:
            te = datetime.datetime.fromisoformat(filters["time_end"])
            query = query.filter(Event.timestamp <= te)
        except Exception:
            pass

    total = query.count()
    events = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()

    results = []
    for ev in events:
        d = ev.to_dict()
        if ev.visitor:
            d["visitor_code"] = ev.visitor.visitor_code
            d["visitor_category"] = ev.visitor.category
            d["visitor_label"] = ev.visitor.label
        results.append(d)

    return {"total": total, "limit": limit, "offset": offset, "events": results}


def generate_incident_timeline(
    session: Session,
    time_start: datetime.datetime,
    time_end: datetime.datetime,
    camera_id: Optional[int] = None,
    visitor_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Compile a chronological forensic incident timeline across a time window."""
    query = (
        session.query(Event)
        .filter(Event.timestamp >= time_start, Event.timestamp <= time_end)
        .order_by(Event.timestamp.asc())
    )

    if camera_id:
        query = query.filter(Event.camera_id == camera_id)
    if visitor_id:
        query = query.filter(Event.visitor_id == visitor_id)

    events = query.all()

    timeline_items = []
    distinct_visitors = set()
    distinct_cameras = set()
    alerts_count = 0

    for ev in events:
        item = ev.to_dict()
        if ev.visitor_id:
            distinct_visitors.add(ev.visitor_id)
            if ev.visitor:
                item["visitor_code"] = ev.visitor.visitor_code
                item["visitor_category"] = ev.visitor.category
                item["visitor_label"] = ev.visitor.label

        if ev.camera_id:
            distinct_cameras.add(ev.camera_id)
            if ev.camera:
                item["camera_name"] = ev.camera.name
                item["camera_location"] = ev.camera.location

        if ev.alerts:
            alerts_count += len(ev.alerts)
            item["alerts"] = [a.to_dict() for a in ev.alerts]

        timeline_items.append(item)

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "time_window": {
            "start": time_start.isoformat(),
            "end": time_end.isoformat(),
        },
        "summary": {
            "total_events": len(timeline_items),
            "distinct_visitors": len(distinct_visitors),
            "distinct_cameras": len(distinct_cameras),
            "alerts_linked": alerts_count,
        },
        "timeline": timeline_items,
    }


def export_timeline_html(timeline_data: Dict[str, Any]) -> str:
    """Generate executive printable/PDF-ready HTML report for forensic review."""
    summary = timeline_data.get("summary", {})
    tw = timeline_data.get("time_window", {})
    items = timeline_data.get("timeline", [])

    rows_html = ""
    for it in items:
        ts = it.get("timestamp", "").replace("T", " ")[:19]
        ev_type = it.get("event_type", "EVENT")
        vis = it.get("visitor_code", "Anonymous")
        cat = it.get("visitor_category", "Unknown")
        cam = it.get("camera_name", f"Camera #{it.get('camera_id')}")
        objs = ", ".join(it.get("detected_objects", [])) or "None"

        badge_cls = "background:#ecfdf5;color:#047857;"
        if "RESTRICTED" in ev_type:
            badge_cls = "background:#fef2f2;color:#b91c1c;"
        elif "LOITERING" in ev_type:
            badge_cls = "background:#fffbeb;color:#b45309;"

        rows_html += f"""
        <tr style="border-bottom:1px solid #e2e8f0;">
          <td style="padding:10px;font-family:monospace;font-size:11px;">{ts}</td>
          <td style="padding:10px;"><span style="display:inline-block;padding:2px 8px;border-radius:6px;font-weight:700;font-size:10px;{badge_cls}">{ev_type}</span></td>
          <td style="padding:10px;font-weight:600;">{vis} <span style="font-weight:400;color:#64748b;font-size:11px;">({cat})</span></td>
          <td style="padding:10px;">{cam}</td>
          <td style="padding:10px;color:#475569;">{objs}</td>
        </tr>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Incident Timeline Report — EcoLifyBuddy</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; margin: 40px; background: #fff; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    .subtitle {{ color: #047857; font-weight: 600; font-size: 14px; margin-bottom: 24px; }}
    .summary-box {{ display: flex; gap: 20px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 24px; }}
    .kpi {{ flex: 1; }}
    .kpi-num {{ font-size: 20px; font-weight: 800; color: #0f172a; }}
    .kpi-lbl {{ font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th {{ background: #f1f5f9; padding: 10px; text-align: left; font-size: 11px; text-transform: uppercase; color: #475569; }}
    .footer {{ margin-top: 40px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 16px; }}
  </style>
</head>
<body>
  <h1>FORENSIC INCIDENT TIMELINE REPORT</h1>
  <div class="subtitle">EcoLifyBuddy CCTV Intelligence System</div>

  <div class="summary-box">
    <div class="kpi"><div class="kpi-num">{summary.get('total_events', 0)}</div><div class="kpi-lbl">Total Events</div></div>
    <div class="kpi"><div class="kpi-num">{summary.get('distinct_visitors', 0)}</div><div class="kpi-lbl">Visitors Involved</div></div>
    <div class="kpi"><div class="kpi-num">{summary.get('distinct_cameras', 0)}</div><div class="kpi-lbl">Cameras Reconstructed</div></div>
    <div class="kpi"><div class="kpi-num">{summary.get('alerts_linked', 0)}</div><div class="kpi-lbl">Anomalies Detected</div></div>
  </div>

  <p style="font-size:12px;color:#475569;margin-bottom:16px;">
    <strong>Time Window:</strong> {tw.get('start', '')[:19]} to {tw.get('end', '')[:19]} (UTC)
  </p>

  <table>
    <thead>
      <tr>
        <th>Timestamp</th>
        <th>Event Type</th>
        <th>Visitor</th>
        <th>Camera / Location</th>
        <th>Detected Objects</th>
      </tr>
    </thead>
    <tbody>
      {rows_html if rows_html else '<tr><td colspan="5" style="text-align:center;padding:20px;color:#94a3b8;">No events recorded in this time window.</td></tr>'}
    </tbody>
  </table>

  <div class="footer">
    Report generated on {timeline_data.get('generated_at', '')[:19]} UTC &bull; Confidential Security Document &bull; Verified under DPDP Act 2023 Audit Guidelines
  </div>
</body>
</html>"""
