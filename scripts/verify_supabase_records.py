import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from database.connection import get_session_factory
from database.models import Visitor, VisitorEntry

session = get_session_factory()()
try:
    visitors = session.query(Visitor).all()
    print(f"=== Total Visitors in Supabase: {len(visitors)} ===")
    for v in visitors:
        print(f"ID: {v.id} | Code: {v.visitor_code} | Name: {v.full_name} | Phone: {v.phone_number} | Plate: {v.vehicle_number} | Status: {v.status}")

    entries = session.query(VisitorEntry).all()
    print(f"\n=== Total Visitor Entries in Supabase: {len(entries)} ===")
    for e in entries:
        print(f"ID: {e.id} | Visitor ID: {e.visitor_id} | Type: {e.event_type} | Source: {e.source} | Confirmed: {e.confirmed} | Time: {e.timestamp}")
finally:
    session.close()
