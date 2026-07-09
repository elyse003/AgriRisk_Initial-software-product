"""Database access for AgriRisk Rwanda.

Runs on PostgreSQL in production and on SQLite locally, through one SQLAlchemy
engine. Set the DATABASE_URL environment variable (or Streamlit secret) to a
Postgres connection string to use Postgres; otherwise a local SQLite file
(data/agririsk.db) is used so the repo still clones-and-runs and the tests pass.

The six tables match schema.sql and the proposal ERD: users, price_records,
risk_scores, input_catalogue, feedback, subscribers. All write helpers fail
quietly so the dashboard keeps working even if the database is briefly down.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, create_engine, delete, func, insert, select, update,
                        inspect, text)
from sqlalchemy.exc import IntegrityError


# ------------------------------------------------------------ password hashing
def hash_password(password: str, iterations: int = 200_000) -> str:
    """Salted PBKDF2-SHA256 hash, stored as algo$iters$salt$hash (stdlib only)."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "agririsk.db"


def database_url() -> str:
    """Postgres URL from DATABASE_URL, else a local SQLite file.

    On Streamlit Cloud the value is stored as a secret rather than an environment
    variable, so we also look in st.secrets (ignored outside a Streamlit app).
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        try:
            import streamlit as st
            url = str(st.secrets.get("DATABASE_URL", "")).strip()
        except Exception:
            url = ""
    if url:
        # accept both postgres:// and postgresql:// and pin the psycopg (v3) driver
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url.split("://", 1)[1]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.split("://", 1)[1]
        return url
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"


_engine = None


def engine():
    """Cached SQLAlchemy engine for the configured database."""
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True, future=True)
    return _engine


def get_connection():
    """Raw DBAPI connection (used by a couple of low-level callers / tests)."""
    return engine().raw_connection()


# --------------------------------------------------------------- schema (ERD)
metadata = MetaData()

users = Table(
    "users", metadata,
    Column("user_id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(120), nullable=False),
    Column("role", String(40), nullable=False),            # farmer | officer | super_admin
    Column("district", String(60)),
    Column("phone", String(20), unique=True),
    Column("language", String(5), default="rw"),
    Column("username", String(40), unique=True),
    Column("password_hash", String(200)),
)
price_records = Table(
    "price_records", metadata,
    Column("record_id", Integer, primary_key=True, autoincrement=True),
    Column("crop", String(40), nullable=False),
    Column("market", String(80), nullable=False),
    Column("record_date", String(20), nullable=False),
    Column("price_rwf", Float, nullable=False),
    UniqueConstraint("crop", "market", "record_date", name="uq_price_records"),
)
risk_scores = Table(
    "risk_scores", metadata,
    Column("score_id", Integer, primary_key=True, autoincrement=True),
    Column("district", String(60), nullable=False),
    Column("season", String(20)),
    Column("rainfall_anomaly", Float),
    Column("cpi_change", Float),
    Column("fertilizer_change", Float),
    Column("risk_level", String(10)),
    Column("scored_at", DateTime, server_default=func.now()),
)
input_catalogue = Table(
    "input_catalogue", metadata,
    Column("input_id", Integer, primary_key=True, autoincrement=True),
    Column("input_name", String(120), nullable=False),
    Column("input_type", String(40)),
    Column("crop_suitability", String(120)),
    Column("supplier", String(120)),
    Column("district", String(60)),
    Column("price_rwf", Float, nullable=False),
)
feedback = Table(
    "feedback", metadata,
    Column("feedback_id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer),
    Column("module_name", String(40)),
    Column("satisfaction_rating", Integer),
    Column("submitted_at", DateTime, server_default=func.now()),
    # --- TAM pilot instrument (RQ4): anonymised participant code + constructs ---
    Column("participant_code", String(16)),      # EO-01..EO-20 / FM-01..FM-20
    Column("participant_role", String(20)),      # extension_officer | farmer
    Column("perceived_usefulness", Integer),     # 1-5 Likert
    Column("perceived_ease_of_use", Integer),    # 1-5 Likert
    Column("confidence", Integer),               # 1-5 Likert (advisory confidence)
    Column("comments", Text),
)

# Columns added after the first release; SQLAlchemy's create_all() will not add
# them to an existing table, so patch them in additively (SQLite + Postgres).
_FEEDBACK_ADDED = {
    "participant_code": "VARCHAR(16)", "participant_role": "VARCHAR(20)",
    "perceived_usefulness": "INTEGER", "perceived_ease_of_use": "INTEGER",
    "confidence": "INTEGER", "comments": "TEXT",
}
subscribers = Table(
    "subscribers", metadata,
    Column("subscriber_id", Integer, primary_key=True, autoincrement=True),
    Column("phone_number", String(20), unique=True, nullable=False),
    Column("district", String(60)),
    Column("crops", String(120)),
    Column("language", String(5), default="rw"),
)

SAMPLE_SUBSCRIBERS = [
    {"phone_number": "0788000101", "district": "Musanze", "crops": "potatoes,maize", "language": "rw"},
    {"phone_number": "0788000102", "district": "Bugesera", "crops": "beans,maize", "language": "rw"},
    {"phone_number": "0788000103", "district": "Nyagatare", "crops": "maize", "language": "en"},
    {"phone_number": "0788000104", "district": "Huye", "crops": "beans,potatoes", "language": "rw"},
    {"phone_number": "0788000105", "district": "Rubavu", "crops": "potatoes", "language": "rw"},
    {"phone_number": "0788000106", "district": "Kirehe", "crops": "maize,beans", "language": "rw"},
    {"phone_number": "0788000107", "district": "Nyamagabe", "crops": "potatoes,beans", "language": "rw"},
    {"phone_number": "0788000108", "district": "Gatsibo", "crops": "maize", "language": "en"},
]
# Demo accounts (username / password) for the login. Passwords are hashed at
# seed time; these plaintext values are documented in the README for the demo.
SAMPLE_USERS = [
    {"name": "National Administrator (RAB)", "role": "super_admin", "district": "Nationwide", "phone": "0788000001", "language": "en", "username": "admin", "password": "admin123"},
    {"name": "Extension Officer, Musanze", "role": "officer", "district": "Musanze", "phone": "0788000010", "language": "rw", "username": "musanze", "password": "officer123"},
    {"name": "Extension Officer, Bugesera", "role": "officer", "district": "Bugesera", "phone": "0788000011", "language": "rw", "username": "bugesera", "password": "officer123"},
    {"name": "Jean (farmer)", "role": "farmer", "district": "Musanze", "phone": "0788000101", "language": "rw", "username": "jean", "password": "farmer123"},
    {"name": "Aline (farmer)", "role": "farmer", "district": "Bugesera", "phone": "0788000102", "language": "rw", "username": "aline", "password": "farmer123"},
    {"name": "Eric (farmer)", "role": "farmer", "district": "Nyagatare", "phone": "0788000103", "language": "en", "username": "eric", "password": "farmer123"},
]


# ----------------------------------------------------------------- lifecycle
def init_db(seed: bool = True):
    """Create the tables (dialect-appropriate) and optionally seed sample rows."""
    metadata.create_all(engine())
    if seed:
        _seed()


def _seed():
    eng = engine()
    with eng.begin() as conn:
        if conn.execute(select(func.count()).select_from(input_catalogue)).scalar() == 0:
            csv = ROOT / "data" / "processed" / "minagri_input_prices.csv"
            if not csv.exists():
                csv = ROOT / "data" / "raw" / "minagri_input_prices.csv"
            if csv.exists():
                df = pd.read_csv(csv)
                rows = [{"input_name": r.get("input_name"), "input_type": r.get("input_type"),
                         "crop_suitability": r.get("crop_suitability"),
                         "supplier": r.get("supplier", "Smart Nkunganire System"),
                         "district": r.get("district", "Nationwide"),
                         "price_rwf": float(r["price_rwf"])} for _, r in df.iterrows()]
                if rows:
                    conn.execute(insert(input_catalogue), rows)
        if conn.execute(select(func.count()).select_from(subscribers)).scalar() == 0:
            conn.execute(insert(subscribers), SAMPLE_SUBSCRIBERS)
        if conn.execute(select(func.count()).select_from(users)).scalar() == 0:
            rows = [{**{k: v for k, v in u.items() if k != "password"},
                     "password_hash": hash_password(u["password"])} for u in SAMPLE_USERS]
            conn.execute(insert(users), rows)


_initialised = False


def _migrate_feedback():
    """Additively add the TAM columns to an existing feedback table (no data loss)."""
    try:
        existing = {c["name"] for c in inspect(engine()).get_columns("feedback")}
        missing = {k: v for k, v in _FEEDBACK_ADDED.items() if k not in existing}
        if not missing:
            return
        with engine().begin() as conn:
            for col, sqltype in missing.items():
                conn.execute(text(f"ALTER TABLE feedback ADD COLUMN {col} {sqltype}"))
    except Exception:
        pass          # never block the app on a migration


def _ensure():
    global _initialised
    if _initialised:
        return
    try:
        init_db()
        _migrate_feedback()
    except Exception:
        pass
    _initialised = True


# ------------------------------------------------------------------ reads
def fetch_catalogue():
    """Input catalogue from the database, falling back to the CSV if needed."""
    _ensure()
    try:
        with engine().connect() as conn:
            df = pd.read_sql_query(
                select(input_catalogue.c.input_id, input_catalogue.c.input_name,
                       input_catalogue.c.input_type, input_catalogue.c.crop_suitability,
                       input_catalogue.c.supplier, input_catalogue.c.district,
                       input_catalogue.c.price_rwf), conn)
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
        with engine().connect() as conn:
            return int(conn.execute(select(func.count()).select_from(subscribers)).scalar() or 0)
    except Exception:
        return 0


def list_subscribers():
    _ensure()
    try:
        with engine().connect() as conn:
            return pd.read_sql_query(
                select(subscribers.c.phone_number, subscribers.c.district,
                       subscribers.c.crops, subscribers.c.language), conn)
    except Exception:
        return pd.DataFrame()


# ------------------------------------------------------------------ writes
def add_subscriber(phone, district, crops, language="rw"):
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(subscribers).values(
                phone_number=phone, district=district, crops=crops, language=language))
        return True
    except IntegrityError:
        return False   # phone already subscribed
    except Exception:
        return False


def remove_subscriber(phone):
    """Opt-out: delete the subscription for this phone. Returns True if removed."""
    _ensure()
    try:
        with engine().begin() as conn:
            return conn.execute(
                delete(subscribers).where(subscribers.c.phone_number == phone)).rowcount > 0
    except Exception:
        return False


def user_district(phone):
    """District of a registered user with this phone (to seed a subscription), or None."""
    _ensure()
    try:
        with engine().connect() as conn:
            row = conn.execute(
                select(users.c.district).where(users.c.phone == phone)).first()
            return row[0] if row else None
    except Exception:
        return None


def log_risk(district, season, rainfall_anomaly, cpi_change, fertilizer_change, risk_level):
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(risk_scores).values(
                district=district, season=season, rainfall_anomaly=float(rainfall_anomaly),
                cpi_change=float(cpi_change), fertilizer_change=float(fertilizer_change),
                risk_level=risk_level))
    except Exception:
        pass


def log_price(crop, market, record_date, price_rwf):
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(price_records).values(
                crop=crop, market=market, record_date=str(record_date), price_rwf=float(price_rwf)))
    except IntegrityError:
        pass   # one price per crop/market/date
    except Exception:
        pass


def submit_feedback(user_id, module_name, satisfaction_rating):
    """Store a 1-5 satisfaction rating for a module (the feedback table)."""
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(feedback).values(
                user_id=user_id, module_name=module_name,
                satisfaction_rating=int(satisfaction_rating)))
        return True
    except Exception:
        return False


def submit_tam_feedback(participant_code, participant_role, module_name,
                        perceived_usefulness, perceived_ease_of_use,
                        satisfaction_rating, confidence, comments=None, user_id=None):
    """Store one anonymised TAM questionnaire response (RQ4 pilot instrument).

    No names or phone numbers are stored, only the participant code (EO-01/FM-01),
    matching the consent + anonymisation protocol in the proposal's ethics section.
    """
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(feedback).values(
                user_id=user_id, module_name=module_name,
                participant_code=(participant_code or "").strip().upper(),
                participant_role=participant_role,
                perceived_usefulness=int(perceived_usefulness),
                perceived_ease_of_use=int(perceived_ease_of_use),
                satisfaction_rating=int(satisfaction_rating),
                confidence=int(confidence),
                comments=(comments or None)))
        return True
    except Exception:
        return False


def fetch_feedback():
    """All TAM responses as a DataFrame (for scripts/export_feedback.py)."""
    _ensure()
    try:
        with engine().connect() as conn:
            return pd.read_sql(select(feedback), conn)
    except Exception:
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# User roles: how the system knows whether someone is a farmer, an officer, or
# the super admin. The web platform looks a person up on sign-in; the chatbot
# looks them up by phone number when they send a message.
# ---------------------------------------------------------------------------
def authenticate(username, password):
    """Return the user dict (without the hash) if credentials match, else None."""
    _ensure()
    try:
        with engine().connect() as conn:
            row = conn.execute(select(users).where(users.c.username == username)).mappings().first()
        if row and verify_password(password, row.get("password_hash") or ""):
            user = dict(row)
            user.pop("password_hash", None)
            return user
        return None
    except Exception:
        return None


def add_user(name, role, district=None, phone=None, language="rw", username=None, password=None):
    """Register a user. role is 'farmer', 'officer' or 'super_admin'."""
    _ensure()
    try:
        values = dict(name=name, role=role, district=district, phone=phone,
                      language=language, username=username)
        if password:
            values["password_hash"] = hash_password(password)
        with engine().begin() as conn:
            conn.execute(insert(users).values(**values))
        return True
    except IntegrityError:
        return False   # phone or username already registered
    except Exception:
        return False


def get_user_by_phone(phone):
    """Identify a user from their phone number; returns a dict or None."""
    _ensure()
    try:
        with engine().connect() as conn:
            row = conn.execute(select(users).where(users.c.phone == phone)).mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


def get_user_by_username(username):
    """Fetch a user dict (without the password hash) by username, or None. Used to
    restore a signed-in session from a token after a full page reload."""
    _ensure()
    try:
        with engine().connect() as conn:
            row = conn.execute(select(users).where(users.c.username == username)).mappings().first()
        if not row:
            return None
        user = dict(row)
        user.pop("password_hash", None)
        return user
    except Exception:
        return None


def list_users(role=None):
    """All users (with id + username), optionally filtered to one role."""
    _ensure()
    try:
        q = select(users.c.user_id, users.c.username, users.c.name, users.c.role,
                   users.c.district, users.c.phone, users.c.language).order_by(users.c.role, users.c.name)
        if role:
            q = q.where(users.c.role == role)
        with engine().connect() as conn:
            return pd.read_sql_query(q, conn)
    except Exception:
        return pd.DataFrame()


def role_counts():
    """How many of each role are registered: {'farmer': n, 'officer': n, ...}."""
    _ensure()
    try:
        with engine().connect() as conn:
            rows = conn.execute(select(users.c.role, func.count()).group_by(users.c.role)).all()
        return {r: c for r, c in rows}
    except Exception:
        return {}


# ----------------------------------------------------- admin: manage users
def update_user(user_id, **fields):
    """Update allowed fields (name, role, district, phone, language) for a user."""
    allowed = {k: v for k, v in fields.items()
               if k in ("name", "role", "district", "phone", "language") and v is not None}
    if not allowed:
        return False
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(update(users).where(users.c.user_id == user_id).values(**allowed))
        return True
    except IntegrityError:
        return False
    except Exception:
        return False


def set_password(user_id, new_password):
    """Reset a user's password (admin action)."""
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(update(users).where(users.c.user_id == user_id)
                         .values(password_hash=hash_password(new_password)))
        return True
    except Exception:
        return False


def delete_user(user_id):
    """Remove a user account."""
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(delete(users).where(users.c.user_id == user_id))
        return True
    except Exception:
        return False