"""Create and seed the database. Uses PostgreSQL if DATABASE_URL is set, else a
local SQLite file. Run: python scripts/init_db.py"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.db.connection import init_db, DB_PATH, subscriber_count, fetch_catalogue

init_db()
print(f"Database ready at {DB_PATH}")
print(f"  input catalogue rows: {len(fetch_catalogue())}")
print(f"  subscribers: {subscriber_count()}")
