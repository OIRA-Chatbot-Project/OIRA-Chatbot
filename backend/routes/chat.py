"""Backward-compatible shim."""
from api.routers.chat import router, _clean_answer, _run_post_response_tasks
__all__ = ["router", "_clean_answer", "_run_post_response_tasks"]
