from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Session as DBSession, User as DBUser, Message as DBMessage
from models import SessionInfo, SessionsResponse
from auth import get_current_user, get_user_id_from_token

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionsResponse)
async def get_user_sessions(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve all sessions for the authenticated user
    
    - Returns list of sessions with metadata
    - Used to display session history/switcher
    """
    try:
        # Get user ID from token
        clerk_user_id = get_user_id_from_token(current_user)
        
        # Get user from database
        user = db.query(DBUser).filter(DBUser.clerk_user_id == clerk_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all sessions with message counts (optimized query)
        sessions = db.query(
            DBSession.session_id,
            DBSession.created_at,
            DBSession.updated_at,
            func.count(DBMessage.id).label('message_count')
        ).outerjoin(
            DBMessage, DBMessage.session_id == DBSession.session_id
        ).filter(
            DBSession.user_id == user.id
        ).group_by(
            DBSession.session_id, DBSession.created_at, DBSession.updated_at
        ).order_by(
            DBSession.updated_at.desc()
        ).all()
        
        return SessionsResponse(
            sessions=[
                SessionInfo(
                    session_id=s.session_id,
                    created_at=s.created_at,
                    updated_at=s.updated_at
                )
                for s in sessions
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")
