"""
Database engine, session factory, and FastAPI dependency.

ORM model definitions live in app/data/models/*.py.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Import models so Base.metadata is populated before create_all
from app.data.models import Base  # noqa: F401

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chatbot.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables defined in the ORM models if they do not already exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a per-request SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
