from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.data.models.base import Base


class User(Base):
    """Represents a user authenticated via Clerk"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_facts = Column(Text, nullable=True)  # JSON: {"major": "CS", "year": "junior", ...}

    # Relationships
    sessions = relationship("Session", back_populates="user")
