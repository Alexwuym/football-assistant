"""
Health check schema.
"""
from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    database: str
    environment: str

    class Config:
        from_attributes = True
