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

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import (Column, DateTime, Float, Integer, MetaData, String, Table,
                        UniqueConstraint, create_engine, func, insert, select)
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "agririsk.db"


def database_url() -> str:
    """Postgres URL from DATABASE_URL, else a local SQLite file."""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        # accept both postgres:// and postgresql:// and pin the psycopg2 driver
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url.split("://", 1)[1]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url.split("://", 1)[1]
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
)
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
SAMPLE_USERS = [
    {"name": "National Administrator (RAB)", "role": "super_admin", "district": "Nationwide", "phone": "0788000001", "language": "en"},
    {"name": "Extension Officer, Musanze", "role": "officer", "district": "Musanze", "phone": "0788000010", "language": "rw"},
    {"name": "Extension Officer, Bugesera", "role": "officer", "district": "Bugesera", "phone": "0788000011", "language": "rw"},
    {"name": "Jean (farmer)", "role": "farmer", "district": "Musanze", "phone": "0788000101", "language": "rw"},
    {"name": "Aline (farmer)", "role": "farmer", "district": "Bugesera", "phone": "0788000102", "language": "rw"},
    {"name": "Eric (farmer)", "role": "farmer", "district": "Nyagatare", "phone": "0788000103", "language": "en"},
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
            conn.execute(insert(users), SAMPLE_USERS)


_initialised = False


def _ensure():
    global _initialised
    if _initialised:
        return
    try:
        init_db()
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


# ---------------------------------------------------------------------------
# User roles: how the system knows whether someone is a farmer, an officer, or
# the super admin. The web platform looks a person up on sign-in; the chatbot
# looks them up by phone number when they send a message.
# ---------------------------------------------------------------------------
def add_user(name, role, district=None, phone=None, language="rw"):
    """Register a user. role is 'farmer', 'officer' or 'super_admin'."""
    _ensure()
    try:
        with engine().begin() as conn:
            conn.execute(insert(users).values(
                name=name, role=role, district=district, phone=phone, language=language))
    except IntegrityError:
        pass   # phone already registered
    except Exception:
        pass


def get_user_by_phone(phone):
    """Identify a user from their phone number; returns a dict or None."""
    _ensure()
    try:
        with engine().connect() as conn:
            row = conn.execute(select(users).where(users.c.phone == phone)).mappings().first()
        return dict(row) if row else None
    except Exception:
        return None


def list_users(role=None):
    """All users, optionally filtered to one role."""
    _ensure()
    try:
        q = select(users.c.name, users.c.role, users.c.district, users.c.phone, users.c.language)
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