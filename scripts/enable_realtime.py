import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"prepare_threshold": None})
with engine.connect() as conn:
    try:
        # Check publications
        res = conn.execute(text("SELECT pubname FROM pg_publication;")).fetchall()
        print("Publications:", [r[0] for r in res])
        # Add visitors, visitor_entries, and plate_reads to supabase_realtime publication
        conn.execute(text("ALTER PUBLICATION supabase_realtime ADD TABLE visitors, visitor_entries, plate_reads;"))
        conn.commit()
        print("Successfully enabled realtime for visitors, visitor_entries, and plate_reads!")
    except Exception as e:
        print("Publication check note:", e)
