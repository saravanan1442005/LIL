import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("No DATABASE_URL set.")
    exit(1)

# Ensure psycopg connection string format
conn_str = url.replace("postgresql+psycopg://", "postgresql://")
with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Total tables found in Supabase: {len(tables)}")
        for t in tables:
            print(f"  * {t}")

        # Check columns of visitors table
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'visitors' ORDER BY ordinal_position;")
        cols = cur.fetchall()
        print("\nColumns in 'visitors' table:")
        for col, dtype in cols:
            print(f"  - {col} ({dtype})")
