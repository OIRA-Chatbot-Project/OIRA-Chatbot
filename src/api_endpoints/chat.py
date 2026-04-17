from __future__ import annotations
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from src.api_endpoints.dependencies import get_advising_service, get_chat_history_service
from src.api_endpoints.schemas import (
    AdvisingAnswerResponse,
    AdvisingQuestionRequest,
    InitializeChatRequest,
    InitializeChatResponse,
)
from src.services.advising_service import AdvisingService
from src.services.chat_service import ChatHistoryService
from src.services.contracts import AdvisingQuestion

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/initialize", response_model=InitializeChatResponse)
async def initialize_chat_session(
    request: InitializeChatRequest,
    chat_history_service: ChatHistoryService = Depends(get_chat_history_service),
) -> InitializeChatResponse:
    """Create a new advising chat session."""
    raise NotImplementedError("TODO: implement initialize_chat_session")

@router.post("/batch", response_model=AdvisingAnswerResponse)
async def answer_question(
    request: AdvisingQuestionRequest,
    advising_service: AdvisingService = Depends(get_advising_service),
) -> AdvisingAnswerResponse:
    """Handle non-streamed grounded advising response generation."""
    service_request = AdvisingQuestion(
        user_id=request.user_id,
        session_id=request.session_id,
        question=request.question,
        catalog_version_id=request.catalog_version_id,
        max_recommendations=request.max_recommendations,
    )
    _ = service_request
    _ = advising_service
    raise NotImplementedError("TODO: implement answer_question")

@router.post("/stream")
async def stream_answer(
    request: AdvisingQuestionRequest,
    advising_service: AdvisingService = Depends(get_advising_service),
) -> StreamingResponse:
    """Handle streamed grounded advising response generation."""
    _ = request
    _ = advising_service
    raise NotImplementedError("TODO: implement stream_answer")