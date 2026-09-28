"""
Fixture schemas.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.fixture import FixtureStatus


class FixtureBase(BaseModel):
    """Base fixture schema."""
    fixture_id: str
    match_date: datetime
    round_info: Optional[str] = None
    venue: Optional[str] = None
    referee: Optional[str] = None
    status: FixtureStatus = FixtureStatus.SCHEDULED
    status_short: Optional[str] = None
    elapsed: Optional[int] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    home_halftime_score: Optional[int] = None
    away_halftime_score: Optional[int] = None
    is_jc: int = 0
    jc_issue_no: Optional[str] = None
    is_hot: int = 0
    source: Optional[str] = None


class FixtureCreate(FixtureBase):
    """Schema for creating a fixture."""
    league_id: int
    home_team_id: int
    away_team_id: int


class FixtureTeamInfo(BaseModel):
    """Team info in fixture response."""
    id: int
    team_id: str
    name_cn: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class FixtureLeagueInfo(BaseModel):
    """League info in fixture response."""
    id: int
    league_id: str
    name_cn: str
    name_en: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class FixtureOddsInfo(BaseModel):
    """Odds info in fixture response."""
    id: int
    odds_type: str
    option_code: str
    option_name: Optional[str] = None
    odds_value: float
    handicap: Optional[str] = None
    is_stopped: int
    is_recommended: int
    confidence: Optional[float] = None

    class Config:
        from_attributes = True


class FixtureResponse(FixtureBase):
    """Schema for fixture response with related data."""
    id: int
    league: Optional[FixtureLeagueInfo] = None
    home_team: Optional[FixtureTeamInfo] = None
    away_team: Optional[FixtureTeamInfo] = None
    odds: List[FixtureOddsInfo] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FixtureListResponse(BaseModel):
    """Schema for list of fixtures response."""
    total: int
    items: List[FixtureResponse]


class FixtureFilter(BaseModel):
    """Filter params for fixtures query."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    league_id: Optional[int] = None
    status: Optional[str] = None
    is_jc: Optional[int] = None
    is_hot: Optional[int] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class FixtureBatchCreate(BaseModel):
    """Schema for batch creating fixtures."""
    items: List[FixtureCreate]
