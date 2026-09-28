"""
Team model - represents football teams.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Team(Base):
    """Football team model."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String(50), unique=True, nullable=False, index=True, comment="External team ID")
    name_cn = Column(String(100), nullable=False, comment="Chinese name")
    name_en = Column(String(100), nullable=True, comment="English name")
    short_name = Column(String(50), nullable=True, comment="Short name")
    league_id = Column(Integer, ForeignKey("leagues.id", ondelete="SET NULL"), nullable=True)
    logo_url = Column(Text, nullable=True, comment="Team logo URL")
    founded = Column(Integer, nullable=True, comment="Founded year")
    stadium = Column(String(100), nullable=True, comment="Home stadium")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    league = relationship("League", back_populates="teams")
    home_fixtures = relationship("Fixture", foreign_keys="Fixture.home_team_id", back_populates="home_team", lazy="selectin")
    away_fixtures = relationship("Fixture", foreign_keys="Fixture.away_team_id", back_populates="away_team", lazy="selectin")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name_cn}')>"
