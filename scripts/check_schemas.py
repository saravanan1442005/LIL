import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"prepare_threshold": None})
with engine.connect() as conn:
    try:
        res = conn.execute(text("SELECT schema_name FROM information_schema.schemata;")).fetchall()
        print("Schemas:", [r[0] for r in res])
    except Exception as e:
        print("Schema error:", e)
