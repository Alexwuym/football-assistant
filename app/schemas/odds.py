"""
Odds schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.models.odds import OddsType


class OddsBase(BaseModel):
    """Base odds schema."""
    odds_type: OddsType
    option_code: str
    option_name: Optional[str] = None
    odds_value: float
    handicap: Optional[str] = None
    is_stopped: int = 0
    is_recommended: int = 0
    confidence: Optional[float] = None
    source: Optional[str] = None


class OddsCreate(OddsBase):
    """Schema for creating odds."""
    fixture_id: int


class OddsResponse(OddsBase):
    """Schema for odds response."""
    id: int
    fixture_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class OddsListResponse(BaseModel):
    """Schema for list of odds response."""
    total: int
    items: List[OddsResponse]


class OddsBatchCreate(BaseModel):
    """Schema for batch creating odds."""
    items: List[OddsCreate]
