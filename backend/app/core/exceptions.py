"""
Typed application exceptions.

Services raise these; the FastAPI exception handler in main.py converts them
to HTTPResponse objects so route handlers stay clean.
"""
from typing import Optional


class AppError(Exception):
    """Base class for all application errors."""
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: Optional[str] = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""
    status_code = 404
    detail = "Not found"


class ForbiddenError(AppError):
    """Raised when the caller is not permitted to access a resource."""
    status_code = 403
    detail = "Forbidden"


class ValidationError(AppError):
    """Raised when input fails business-logic validation."""
    status_code = 400
    detail = "Validation error"
