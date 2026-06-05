from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.data.models.base import Base


class Session(Base):
    """Represents a chat session"""
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)  # AI-generated title
    conversation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow())  # type: ignore
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow(), onupdate=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow())  # type: ignore

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
