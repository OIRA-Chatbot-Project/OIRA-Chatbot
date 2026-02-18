"""
Common utility functions used across the backend.
Consolidates duplicate code patterns from route files.
"""

import re
import json
from datetime import datetime
from typing import Optional, Dict, Any
from logger import get_logger

from fastapi import HTTPException
from sqlalchemy.orm import Session

from database import Session as DBSession, User as DBUser
from auth import get_user_id_from_token

logger = get_logger(__name__)


def get_utc_now() -> datetime:
    """Get current UTC time, compatible with Python 3.11+ and earlier versions."""
    if hasattr(datetime, 'UTC'):
        return datetime.now(datetime.UTC)
    return datetime.utcnow()


def get_user_from_token(db: Session, current_user: dict) -> DBUser:
    """
    Extract user from token and fetch from database.
    Raises HTTPException 404 if user not found.

    Args:
        db: Database session
        current_user: Token payload from get_current_user dependency

    Returns:
        DBUser instance
    """
    clerk_user_id = get_user_id_from_token(current_user)
    user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please sign up first.")
    return user


def get_session_for_user(
    db: Session,
    session_id: str,
    user: DBUser,
    create_if_missing: bool = False
) -> DBSession:
    """
    Get a session and verify it belongs to the user.

    Args:
        db: Database session
        session_id: Session ID to look up
        user: User who should own the session
        create_if_missing: If True, create session if it doesn't exist

    Returns:
        DBSession instance

    Raises:
        HTTPException 404 if session not found and create_if_missing is False
        HTTPException 403 if session belongs to different user
    """
    session = db.query(DBSession).filter(DBSession.session_id == session_id).first()

    if not session:
        if create_if_missing:
            session = DBSession(session_id=session_id, user_id=user.id)
            db.add(session)
            db.commit()
            return session
        raise HTTPException(status_code=404, detail="Session not found")

    if session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Session does not belong to user")

    return session


def clean_answer(answer: str) -> str:
    """
    Clean up LLM-generated answer text.
    - Removes inline bracket citations like "[filename, p. 123]"
    - Collapses excessive blank lines
    - Collapses repeated spaces/tabs

    Args:
        answer: Raw answer text from LLM

    Returns:
        Cleaned answer text
    """
    try:
        # Remove inline bracket citations like "[filename, p. 123]"
        cleaned = re.sub(r"\[[^\]]+?,\s*p\.\s*\d+\]", "", answer)
        # Collapse excessive blank lines but preserve markdown line breaks
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Collapse only repeated spaces/tabs (not newlines) to avoid flattening lists
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        return cleaned.strip()
    except Exception:
        return answer


def extract_json_from_text(text: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract and parse JSON object from text that may contain other content.
    This consolidates the repeated pattern of finding '{' and '}' in LLM responses.
    
    Args:
        text: Text that may contain a JSON object
        default: Default value to return if extraction fails
    
    Returns:
        Parsed JSON dict, or default value if extraction/parsing fails
    """
    try:
        # Find JSON boundaries
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.warning(f"JSON extraction failed: {e}")
    
    return default


def extract_json_array_from_text(text: str, default: Optional[list] = None) -> Optional[list]:
    """
    Extract and parse JSON array from text that may contain other content.
    
    Args:
        text: Text that may contain a JSON array
        default: Default value to return if extraction fails
    
    Returns:
        Parsed JSON list, or default value if extraction/parsing fails
    """
    try:
        # Find JSON array boundaries
        json_start = text.find('[')
        json_end = text.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = text[json_start:json_end]
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.warning(f"JSON array extraction failed: {e}")
    
    return default or []


def get_conversation_history(db: Session, session_id: str, before_message_id: int, limit: int = 6) -> list:
    """
    Get conversation history for a session, formatted for the chatbot service.
    Optimized to fetch only needed fields instead of full message objects.

    Args:
        db: Database session
        session_id: Session ID
        before_message_id: Get messages before this ID
        limit: Maximum number of messages to retrieve

    Returns:
        List of dicts with 'role' and 'content' keys, in chronological order
    """
    from database import Message as DBMessage

    # Optimized query: fetch only role and content fields
    history_messages = db.query(DBMessage.role, DBMessage.content).filter(
        DBMessage.session_id == session_id,
        DBMessage.id < before_message_id
    ).order_by(DBMessage.created_at.desc()).limit(limit).all()

    # Convert tuples to dicts and reverse to chronological order
    return [
        {"role": msg[0], "content": msg[1]}
        for msg in reversed(history_messages)
    ]
