"""
Backward-compatible shim - imports from infra/db/.
"""
from infra.db.engine import engine, SessionLocal, Base, init_db, get_db
from infra.db.models import User, Session, Message, Feedback

__all__ = [
    "engine", "SessionLocal", "Base", "init_db", "get_db",
    "User", "Session", "Message", "Feedback",
]
