
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.engine import URL


# Find the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent


def load_database_url():
    env_file = BASE_DIR / ".env"

    if not env_file.exists():
        raise RuntimeError("Missing backend/.env file")

    # Read the DATABASE_URL setting
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()

    raise RuntimeError("DATABASE_URL not found in .env")


DATABASE_URL = os.getenv("DATABASE_URL") or load_database_url()


# Create the SQLAlchemy database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# Create database sessions
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    pass
