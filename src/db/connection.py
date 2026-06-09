"""PostgreSQL connection helper via SQLAlchemy."""
from sqlalchemy import create_engine
from config.settings import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def get_engine():
    return engine
