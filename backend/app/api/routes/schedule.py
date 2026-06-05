"""Schedule upload and recommendation routes."""
from fastapi import APIRouter, Depends, UploadFile, File, Form

from app.api.deps import get_schedule_service, get_user_repo
from app.api.schemas.chat import Citation
from app.api.schemas.schedule import ParsedCourse, ScheduleUploadResponse
from app.core.auth import get_current_user, get_user_id_from_token
from app.data.repositories.user_repository import SQLUserRepository
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/upload", response_model=ScheduleUploadResponse)
async def upload_schedule(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    user_repo: SQLUserRepository = Depends(get_user_repo),
):
    """Process a student's schedule upload and provide course recommendations."""
    clerk_user_id = get_user_id_from_token(current_user)
    contents = await file.read()
    result = schedule_service.process_upload(
        session_id=session_id,
        clerk_user_id=clerk_user_id,
        file_content=contents,
        filename=file.filename or "",
        user_repo=user_repo,
    )
    return ScheduleUploadResponse(
        message_id=result.message_id,
        answer=result.answer,
        citations=[Citation(**c) for c in result.citations],
        session_id=result.session_id,
        schedule_summary=result.schedule_summary,
        parsed_courses=[ParsedCourse(**c) for c in result.parsed_courses],
        schedule_message_id=result.schedule_message_id,
        question_category=result.question_category,
        follow_ups=result.follow_ups,
    )
