from sqlalchemy import Column, String, Integer, DateTime, Text
from datetime import datetime

from app.data.models.base import Base


class Feedback(Base):
    """Stores user feedback on assistant messages"""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    message_id = Column(Integer, index=True, nullable=False)
    rating = Column(Integer, nullable=False)  # 1 for thumbs up, -1 for thumbs down
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
