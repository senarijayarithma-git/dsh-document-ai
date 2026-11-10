
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.engine import URL


# Find the backend directory
BASE_DIR = Path(__file__).resolve().parent.parent



from dotenv import load_dotenv

# Load local configuration without overriding
# environment variables supplied by the test runner
# or production deployment.
load_dotenv(
    dotenv_path=BASE_DIR / ".env",
    override=False,
)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Configure it in the "
        "environment or backend/.env."
    )

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
