"""Test Supabase connection and verify visitor table readiness."""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def test_sqlalchemy_connection():
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        print("[!] DATABASE_URL is not set in .env")
        return False

    print(f"[*] Testing PostgreSQL connection to: {db_url.split('@')[-1] if '@' in db_url else 'configured DB'}")
    try:
        from database.connection import get_engine
        from database import init_db
        engine = get_engine()
        with engine.connect() as conn:
            from sqlalchemy import text
            res = conn.execute(text("SELECT version();")).fetchone()
            print(f"[+] Successfully connected to database: {res[0]}")
        
        print("[*] Initializing tables and pgvector extension on Supabase...")
        init_db()
        print("[+] All visitor tables, indexes, and extensions verified successfully on Supabase!")
        return True
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        return False

def test_supabase_rest():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        print("[!] SUPABASE_URL or SUPABASE_KEY not set for REST API test")
        return False
    
    try:
        import urllib.request
        import json
        req = urllib.request.Request(f"{url}/rest/v1/visitors?select=count", headers={
            "apikey": key,
            "Authorization": f"Bearer {key}"
        })
        with urllib.request.urlopen(req) as resp:
            data = resp.read().decode("utf-8")
            print(f"[+] Supabase REST API connection successful. Response: {data}")
            return True
    except Exception as e:
        print(f"[-] Supabase REST API check: {e}")
        return False

if __name__ == "__main__":
    print("=== Supabase Connection Test ===")
    pg_ok = test_sqlalchemy_connection()
    rest_ok = test_supabase_rest()
    if not pg_ok and not rest_ok:
        sys.exit(1)
