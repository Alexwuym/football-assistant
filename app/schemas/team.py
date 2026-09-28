"""
Team schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TeamBase(BaseModel):
    """Base team schema."""
    team_id: str
    name_cn: str
    name_en: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    founded: Optional[int] = None
    stadium: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a team."""
    league_id: Optional[int] = None


class TeamResponse(TeamBase):
    """Schema for team response."""
    id: int
    league_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeamListResponse(BaseModel):
    """Schema for list of teams response."""
    total: int
    items: List[TeamResponse]
