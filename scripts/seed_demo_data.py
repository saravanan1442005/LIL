"""Seed demonstration script for EcoLifyBuddy.
Populates rich mock visitor profiles, 512-d Re-ID feature embeddings,
time-stamped camera events, anomaly alerts, and IoT sensor records.
Ensures the dashboard is 100% demo-ready immediately without live camera hardware.
"""
import os
import sys
import datetime
import random
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import init_db
from database.connection import get_session_factory
from database.models import Visitor, VisitorEmbedding, Event, Alert, Camera, Zone, SensorEvent
from services.vector_store import get_vector_store


def seed_demo():
    print("[*] Initializing database schema...")
    init_db(seed_admin=True, seed_default_cameras=True)

    session = get_session_factory()()
    vstore = get_vector_store(session)

    try:
        # Check if already seeded
        if session.query(Visitor).count() >= 5:
            print("[+] Database already contains demo visitors. Skipping duplicate seeding.")
            return

        print("[+] Seeding realistic recurring visitor profiles & embeddings...")
        now = datetime.datetime.now(datetime.timezone.utc)

        sample_visitors = [
            ("VIS-10001", "Delivery", "Amazon Logistics Express", "Verified delivery agent with daily morning drop", 14),
            ("VIS-10002", "Technician", "Urban Company - AC Maintenance", "Authorized technician for Block A & B", 6),
            ("VIS-10003", "Vendor", "Daily Fresh Organics", "Weekly vegetable & grocery supplier", 21),
            ("VIS-10004", "Domestic Worker", "Shanti - Housekeeping", "Registered domestic staff for Tower 2", 48),
            ("VIS-10005", "Guest", "Guest of Resident 304", "Visiting family members", 2),
            ("VIS-10006", "Delivery", "Zomato Food Courier", "Frequent evening food deliveries", 11),
            ("VIS-10007", "Technician", "BSNL Fiber Broadband", "Network installation team", 4),
        ]

        created_visitors = []
        for code, cat, label, notes, visits in sample_visitors:
            days_ago = random.randint(10, 45)
            first_seen = now - datetime.timedelta(days=days_ago, hours=random.randint(1, 8))
            last_seen = now - datetime.timedelta(hours=random.randint(0, 12), minutes=random.randint(5, 50))

            v = Visitor(
                visitor_code=code,
                category=cat,
                label=label,
                notes=notes,
                first_seen=first_seen,
                last_seen=last_seen,
                total_visits=visits,
                avg_dwell_time=round(random.uniform(45.0, 360.0), 1),
                status="ACTIVE",
            )
            session.add(v)
            session.commit()
            created_visitors.append(v)

            # Generate 2 realistic 512-d appearance embeddings per visitor
            for emb_idx in range(2):
                vec = np.random.normal(loc=0.0, scale=0.1, size=512).astype(np.float32)
                # Bias vector components based on visitor category to simulate consistent clothing colors
                if cat == "Delivery":
                    vec[0:20] += 0.8  # Blue/red courier uniform
                elif cat == "Technician":
                    vec[20:40] += 0.9  # Khaki/work vest
                elif cat == "Domestic Worker":
                    vec[40:60] += 0.7

                norm = np.linalg.norm(vec)
                vec = vec / norm
                vstore.add_embedding(v.id, [round(float(x), 6) for x in vec], embedding_type="reid", camera_id=1, confidence=0.96)

        print("[+] Seeding chronological events across cameras...")
        cameras = session.query(Camera).all()
        cam_ids = [c.id for c in cameras] or [1, 2, 3]

        event_definitions = [
            ("ENTRY", ["backpack", "box"], "North Turnstile Tripwire Crossing"),
            ("ZONE_ENTER", ["box"], "Delivery Loading Bay Entry"),
            ("OBJECT_CARRIED", ["box", "cell phone"], "Package handoff at reception"),
            ("LOITERING", ["backpack"], "Prolonged dwell in restricted corridor"),
            ("RESTRICTED_ZONE", [], "Unauthorized access to server room perimeter"),
            ("EXIT", [], "South Exit Tripwire Crossing"),
            ("ENTRY", ["suitcase"], "Guest entry with luggage"),
            ("ODD_HOUR_VISIT", [], "Late night entry at Gate 1"),
        ]

        created_events = []
        for i in range(25):
            ev_type, objs, desc = random.choice(event_definitions)
            vis = random.choice(created_visitors)
            cam_id = random.choice(cam_ids)
            hours_offset = random.randint(0, 48)
            ev_time = now - datetime.timedelta(hours=hours_offset, minutes=random.randint(0, 59))

            ev = Event(
                event_type=ev_type,
                visitor_id=vis.id,
                camera_id=cam_id,
                zone_id=1,
                track_id=100 + i,
                timestamp=ev_time,
                duration_seconds=round(random.uniform(15.0, 180.0), 1),
                detected_objects=objs,
                confidence=round(random.uniform(0.85, 0.99), 2),
                details={"simulated": True, "description": desc},
            )
            session.add(ev)
            session.commit()
            created_events.append(ev)

        print("[+] Seeding anomaly alerts...")
        sample_alerts = [
            ("RESTRICTED_ZONE_INTRUSION", "CRITICAL", "Unauthorized person detected inside Server Room Perimeter on Camera #1."),
            ("PROLONGED_LOITERING", "HIGH", "Individual dwell time exceeded 120s limit near Cargo Bay Gate 2."),
            ("ODD_HOUR_VISIT", "MEDIUM", "Unscheduled late-night entry detected at 02:43 UTC on Camera #2."),
            ("UNATTENDED_OBJECT", "HIGH", "Unattended package detected near Reception without nearby person for 45s."),
        ]

        for atype, sev, msg in sample_alerts:
            a = Alert(
                event_id=created_events[random.randint(0, len(created_events) - 1)].id,
                alert_type=atype,
                severity=sev,
                message=msg,
                status=random.choice(["NEW", "ACKNOWLEDGED", "RESOLVED"]),
                created_at=now - datetime.timedelta(hours=random.randint(1, 18)),
            )
            session.add(a)
        session.commit()

        print("[+] Seeding IoT sensor events (PIR, RFID, Door)...")
        sensor_samples = [
            ("GATE-1-PIR", "PIR", {"motion": True, "zone": "Turnstile"}),
            ("GATE-1-RFID", "RFID", {"rfid_tag": "TAG-882194", "status": "AUTHORIZED", "badge_holder": "Shanti"}),
            ("DOOR-MAG-B2", "DOOR", {"door_state": "OPEN", "duration_sec": 12}),
            ("GATE-2-QR", "QR", {"qr_pass": "GUEST-PASS-9902", "valid": True}),
        ]

        for sid, stype, data in sensor_samples:
            s_ev = SensorEvent(
                sensor_id=sid,
                sensor_type=stype,
                zone_id=1,
                event_data=data,
                timestamp=now - datetime.timedelta(minutes=random.randint(5, 120)),
                linked_visitor_id=created_visitors[0].id,
            )
            session.add(s_ev)
        session.commit()

        print("[DONE] Demo data seeded successfully! Visitors, embeddings, events, alerts, and sensors are active.")

    finally:
        session.close()


if __name__ == "__main__":
    seed_demo()
