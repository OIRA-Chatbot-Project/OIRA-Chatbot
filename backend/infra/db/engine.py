"""Database engine, session factory, and initialization."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.settings import settings

_db_url = settings.db.DATABASE_URL

connect_args = {}
if _db_url.startswith("sqlite"):
    connect_args = {
        "check_same_thread": False,
        "timeout": 30,
    }

engine = create_engine(
    _db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Initialize database tables."""
    from infra.db.models import User, Session, Message, Feedback  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
