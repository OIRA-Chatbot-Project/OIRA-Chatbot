"""Request-scoped FastAPI dependencies."""
from infra.db.engine import SessionLocal


def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
