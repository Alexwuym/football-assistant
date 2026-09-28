"""
Fixture model - represents football matches/fixtures.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class FixtureStatus(str, PyEnum):
    """Match status enum."""
    SCHEDULED = "SCHEDULED"      # 未开始
    LIVE = "LIVE"                # 进行中
    HALFTIME = "HALFTIME"        # 半场休息
    FINISHED = "FINISHED"        # 已结束
    POSTPONED = "POSTPONED"      # 推迟
    CANCELLED = "CANCELLED"      # 取消
    SUSPENDED = "SUSPENDED"      # 中断


class Fixture(Base):
    """Football match/fixture model."""
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fixture_id = Column(String(50), unique=True, nullable=False, index=True, comment="External fixture ID")
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    away_team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)

    # Match info
    match_date = Column(DateTime, nullable=False, index=True, comment="Match date and time")
    round_info = Column(String(50), nullable=True, comment="Round/Stage info")
    venue = Column(String(100), nullable=True, comment="Match venue")
    referee = Column(String(100), nullable=True, comment="Referee")

    # Status
    status = Column(Enum(FixtureStatus), default=FixtureStatus.SCHEDULED, nullable=False, index=True)
    status_short = Column(String(20), nullable=True, comment="Short status text")
    elapsed = Column(Integer, nullable=True, comment="Elapsed minutes")

    # Scores (nullable until match starts)
    home_score = Column(Integer, nullable=True, comment="Home team score")
    away_score = Column(Integer, nullable=True, comment="Away team score")
    home_halftime_score = Column(Integer, nullable=True, comment="Home halftime score")
    away_halftime_score = Column(Integer, nullable=True, comment="Away halftime score")

    # Additional info
    is_jc = Column(Integer, default=0, nullable=False, comment="Is Jingcai (竞彩) available: 0=no, 1=yes")
    jc_issue_no = Column(String(20), nullable=True, comment="Jingcai issue number")
    is_hot = Column(Integer, default=0, nullable=False, comment="Is hot match: 0=no, 1=yes")
    source = Column(String(50), nullable=True, comment="Data source")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    league = relationship("League", back_populates="fixtures")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_fixtures")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_fixtures")
    odds = relationship("Odds", back_populates="fixture", lazy="selectin", cascade="all, delete-orphan")

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("idx_fixture_date_league", "match_date", "league_id"),
        Index("idx_fixture_date_status", "match_date", "status"),
        Index("idx_fixture_jc", "is_jc", "match_date"),
    )

    def __repr__(self):
        return f"<Fixture(id={self.id}, fixture_id={self.fixture_id})>"
