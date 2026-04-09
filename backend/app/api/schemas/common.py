from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="API status")
    version: str = Field(..., description="API version")
