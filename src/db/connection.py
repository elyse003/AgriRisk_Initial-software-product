"""SQLite database access for AgriRisk Rwanda.

The production schema (PostgreSQL) is defined in schema.sql. For the prototype the
same six tables run on a local SQLite database, so the application stores and reads
data without a separate database server. All write helpers fail quietly so the
dashboard keeps working even if the database file is unavailable.
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "agririsk.db"

DDL = """
CREATE TABLE IF NOT EXISTS users (
    user_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    role     TEXT NOT NULL,        -- 'farmer' | 'officer' | 'super_admin'
    district TEXT,
    phone    TEXT UNIQUE,
    language TEXT DEFAULT 'rw'
);
CREATE TABLE IF NOT EXISTS price_records (
    record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    crop        TEXT NOT NULL,
    market      TEXT NOT NULL,
    record_date TEXT NOT NULL,
    price_rwf   REAL NOT NULL,
    UNIQUE (crop, market, record_date)
);
CREATE TABLE IF NOT EXISTS risk_scores (
    score_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    district          TEXT NOT NULL,
    season            TEXT,
    rainfall_anomaly  REAL,
    cpi_change        REAL,
    fertilizer_change REAL,
    risk_level        TEXT,
    scored_at         TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS input_catalogue (
    input_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    input_name       TEXT NOT NULL,
    input_type       TEXT,
    crop_suitability TEXT,
    supplier         TEXT,
    district         TEXT,
    price_rwf        REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER,
    module_name         TEXT,
    satisfaction_rating INTEGER,
    submitted_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subscribers (
    subscriber_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number  TEXT UNIQUE NOT NULL,
    district      TEXT,
    crops         TEXT,
    language      TEXT DEFAULT 'rw'
);
"""

SAMPLE_SUBSCRIBERS = [
    ("0788000101", "Musanze", "potatoes,maize", "rw"),
    ("0788000102", "Bugesera", "beans,maize", "rw"),
    ("0788000103", "Nyagatare", "maize", "en"),
    ("0788000104", "Huye", "beans,potatoes", "rw"),
    ("0788000105", "Rubavu", "potatoes", "rw"),
    ("0788000106", "Kirehe", "maize,beans", "rw"),
    ("0788000107", "Nyamagabe", "potatoes,beans", "rw"),
    ("0788000108", "Gatsibo", "maize", "en"),
]

# name, role, district, phone, language. Roles: 'farmer' | 'officer' | 'super_admin'
SAMPLE_USERS = [
    ("National Administrator (RAB)", "super_admin", "Nationwide", "0788000001", "en"),
    ("Extension Officer - Musanze", "officer", "Musanze", "0788000010", "rw"),
    ("Extension Officer - Bugesera", "officer", "Bugesera", "0788000011", "rw"),
    ("Jean (farmer)", "farmer", "Musanze", "0788000101", "rw"),
    ("Aline (farmer)", "farmer", "Bugesera", "0788000102", "rw"),
    ("Eric (farmer)", "farmer", "Nyagatare", "0788000103", "en"),
]


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db(seed=True):
    conn = get_connection()
    conn.executescript(DDL)
    conn.commit()
    if seed:
        _seed(conn)
    conn.close()


def _seed(conn):
    cur = conn.cursor()
    if cur.execute("SELECT COUNT(*) FROM input_catalogue").fetchone()[0] == 0:
        csv = ROOT / "data" / "processed" / "minagri_input_prices.csv"
        if not csv.exists():
            csv = ROOT / "data" / "raw" / "minagri_input_prices.csv"
        if csv.exists():
            df = pd.read_csv(csv)
            for _, r in df.iterrows():
                cur.execute(
                    "INSERT INTO input_catalogue (input_name, input_type, crop_suitability, supplier, district, price_rwf)"
                    " VALUES (?,?,?,?,?,?)",
                    (r.get("input_name"), r.get("input_type"), r.get("crop_suitability"),
                     r.get("supplier", "Smart Nkunganire System"), r.get("district", "Nationwide"),
                     float(r["price_rwf"])))
    if cur.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0] == 0:
        cur.executemany(
            "INSERT OR IGNORE INTO subscribers (phone_number, district, crops, language) VALUES (?,?,?,?)",
            SAMPLE_SUBSCRIBERS)
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.executemany(
            "INSERT OR IGNORE INTO users (name, role, district, phone, language) VALUES (?,?,?,?,?)",
            SAMPLE_USERS)
    conn.commit()


def _ensure():
    if not DB_PATH.exists():
        init_db()


def fetch_catalogue():
    """Return the input catalogue from the database, falling back to the CSV."""
    _ensure()
    try:
        conn = get_connection()
        df = pd.read_sql_query(
            "SELECT input_id, input_name, input_type, crop_suitability, supplier, district, price_rwf"
            " FROM input_catalogue", conn)
        conn.close()
        if len(df):
            return df
    except Exception:
        pass
    for p in [ROOT / "data" / "processed" / "minagri_input_prices.csv",
              ROOT / "data" / "raw" / "minagri_input_prices.csv"]:
        if p.exists():
            return pd.read_csv(p)
    return pd.DataFrame()


def subscriber_count():
    _ensure()
    try:
        conn = get_connection()
        n = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        conn.close()
        return int(n)
    except Exception:
        return 0


def add_subscriber(phone, district, crops, language="rw"):
    _ensure()
    try:
        conn = get_connection()
        conn.execute("INSERT OR IGNORE INTO subscribers (phone_number, district, crops, language) VALUES (?,?,?,?)",
                     (phone, district, crops, language))
        conn.commit(); conn.close()
        return True
    except Exception:
        return False


def list_subscribers():
    _ensure()
    try:
        conn = get_connection()
        df = pd.read_sql_query("SELECT phone_number, district, crops, language FROM subscribers", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


def log_risk(district, season, rainfall_anomaly, cpi_change, fertilizer_change, risk_level):
    _ensure()
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO risk_scores (district, season, rainfall_anomaly, cpi_change, fertilizer_change, risk_level)"
            " VALUES (?,?,?,?,?,?)",
            (district, season, float(rainfall_anomaly), float(cpi_change), float(fertilizer_change), risk_level))
        conn.commit(); conn.close()
    except Exception:
        pass


def log_price(crop, market, record_date, price_rwf):
    _ensure()
    try:
        conn = get_connection()
        conn.execute("INSERT OR IGNORE INTO price_records (crop, market, record_date, price_rwf) VALUES (?,?,?,?)",
                     (crop, market, str(record_date), float(price_rwf)))
        conn.commit(); conn.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# User roles: how the system knows whether someone is a farmer, an officer,
# or the super admin. The web platform looks a person up on sign-in; the
# chatbot looks them up by phone number when they send a message.
# ---------------------------------------------------------------------------
def add_user(name, role, district=None, phone=None, language="rw"):
    """Register a user. role is 'farmer', 'officer' or 'super_admin'."""
    _ensure()
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO users (name, role, district, phone, language) VALUES (?,?,?,?,?)",
        (name, role, district, phone, language))
    conn.commit(); conn.close()


def get_user_by_phone(phone):
    """Identify who is using the service from their phone number.

    Returns a dict with their role, district and language, or None if unknown.
    This is how the chatbot decides what a caller is allowed to see.
    """
    _ensure()
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, name, role, district, phone, language FROM users WHERE phone = ?",
        (phone,)).fetchone()
    conn.close()
    if not row:
        return None
    keys = ["user_id", "name", "role", "district", "phone", "language"]
    return dict(zip(keys, row))


def list_users(role=None):
    """All users, optionally filtered to one role."""
    _ensure()
    conn = get_connection()
    if role:
        df = pd.read_sql_query(
            "SELECT name, role, district, phone, language FROM users WHERE role = ?", conn, params=(role,))
    else:
        df = pd.read_sql_query("SELECT name, role, district, phone, language FROM users", conn)
    conn.close()
    return df


def role_counts():
    """How many of each role are registered: {'farmer': n, 'officer': n, ...}."""
    _ensure()
    conn = get_connection()
    rows = conn.execute("SELECT role, COUNT(*) FROM users GROUP BY role").fetchall()
    conn.close()
    return {r: c for r, c in rows}
