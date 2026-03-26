"""
Session management routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import func
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from infra.db.engine import get_db
from infra.db.models import Session as DBSession, User as DBUser, Message as DBMessage
from api.schemas import SessionInfo, SessionsResponse
from auth import get_current_user, get_user_id_from_token
from core.settings import settings

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionsResponse)
async def get_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all sessions for the authenticated user."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        sessions = db.query(
            DBSession.session_id,
            DBSession.title,
            DBSession.created_at,
            DBSession.updated_at,
            func.count(DBMessage.id).label('message_count')
        ).outerjoin(
            DBMessage, DBMessage.session_id == DBSession.session_id
        ).filter(
            DBSession.user_id == user.id
        ).group_by(
            DBSession.session_id, DBSession.title, DBSession.created_at, DBSession.updated_at
        ).order_by(
            DBSession.updated_at.desc()
        ).all()

        return SessionsResponse(
            sessions=[
                SessionInfo(
                    session_id=s.session_id,
                    title=s.title,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                    has_messages=s.message_count > 0
                )
                for s in sessions
                if s.message_count > 0
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a session and its messages for the authenticated user."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session = db.query(DBSession).filter(
            DBSession.session_id == session_id,
            DBSession.user_id == user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        db.query(DBMessage).filter(DBMessage.session_id == session_id).delete(synchronize_session=False)
        db.delete(session)
        db.commit()

        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


class GenerateTitleRequest(BaseModel):
    session_id: str
    first_message: str


class GenerateTitleResponse(BaseModel):
    title: str


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None


@router.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_session_title(
    request: GenerateTitleRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an AI-powered title for a chat session based on the first message."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)

        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session = db.query(DBSession).filter(
            DBSession.session_id == request.session_id,
            DBSession.user_id == user.id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        llm = ChatOpenAI(
            api_key=settings.llm.OPENAI_API_KEY,
            model=settings.llm.OPENAI_LIGHT_MODEL,
            temperature=0.7
        )

        prompt = f"""Generate a concise, descriptive title (3-5 words maximum) for a chat conversation that starts with this message:

"{request.first_message}"

Requirements:
- Keep it under 50 characters
- Make it descriptive but concise
- Use title case
- No quotes or special formatting
- Example: "Computer Science Requirements" or "CSCI 204 Prerequisites"

Title:"""

        response = llm.invoke(prompt)
        title = response.content.strip()

        title = title.replace('"', '').replace("'", "").strip()
        if len(title) > 60:
            title = title[:57] + "..."

        session.title = title
        db.commit()

        return GenerateTitleResponse(title=title)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to generate title: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating title: {str(e)}")


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a session's title."""
    try:
        clerk_user_id = get_user_id_from_token(current_user)
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        session = db.query(DBSession).filter(
            DBSession.session_id == session_id,
            DBSession.user_id == user.id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if request.title is not None:
            title = request.title.strip()
            if not title:
                raise HTTPException(status_code=400, detail="Title cannot be empty")
            session.title = title

        db.commit()

        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating session: {str(e)}")
