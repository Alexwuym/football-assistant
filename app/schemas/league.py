"""
League schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class LeagueBase(BaseModel):
    """Base league schema."""
    league_id: str
    name_cn: str
    name_en: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    season: Optional[str] = None


class LeagueCreate(LeagueBase):
    """Schema for creating a league."""
    pass


class LeagueResponse(LeagueBase):
    """Schema for league response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeagueListResponse(BaseModel):
    """Schema for list of leagues response."""
    total: int
    items: List[LeagueResponse]
