import os
import sqlite3
import psycopg
from dotenv import load_dotenv

load_dotenv()
pg_url = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
sqlite_path = "d:/LIL/data/ecolifybuddy_dev.db"

if not os.path.exists(sqlite_path):
    print("No local SQLite database found.")
    exit(0)

s_conn = sqlite3.connect(sqlite_path)
s_cur = s_conn.cursor()

# Check tables
s_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
s_tables = [r[0] for r in s_cur.fetchall()]
print("SQLite tables:", s_tables)

if "visitors" in s_tables:
    s_cur.execute("SELECT count(*) FROM visitors;")
    v_count = s_cur.fetchone()[0]
    print(f"Visitors in SQLite: {v_count}")
    if v_count > 0:
        s_cur.execute("SELECT id, visitor_code, full_name, phone_number, vehicle_number, status FROM visitors LIMIT 10;")
        for row in s_cur.fetchall():
            print(f"  Visitor: id={row[0]}, code={row[1]}, name={row[2]}, phone={row[3]}, vehicle={row[4]}, status={row[5]}")

if "visitor_entries" in s_tables:
    s_cur.execute("SELECT count(*) FROM visitor_entries;")
    print(f"Visitor entries in SQLite: {s_cur.fetchone()[0]}")

s_conn.close()
