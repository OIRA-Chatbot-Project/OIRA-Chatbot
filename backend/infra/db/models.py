"""ORM models for the database."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from infra.db.engine import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    clerk_user_id = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_facts = Column(Text, nullable=True)
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    conversation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow())  # type: ignore
    updated_at = Column(DateTime, default=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow(), onupdate=lambda: datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow())  # type: ignore
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    citations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="messages")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    message_id = Column(Integer, index=True, nullable=False)
    rating = Column(Integer, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
