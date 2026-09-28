"""
League model - represents football leagues/competitions.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class League(Base):
    """League/Competition model."""
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String(50), unique=True, nullable=False, index=True, comment="External league ID")
    name_cn = Column(String(100), nullable=False, comment="Chinese name")
    name_en = Column(String(100), nullable=True, comment="English name")
    country = Column(String(50), nullable=True, comment="Country")
    logo_url = Column(Text, nullable=True, comment="League logo URL")
    season = Column(String(20), nullable=True, comment="Current season")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    teams = relationship("Team", back_populates="league", lazy="selectin")
    fixtures = relationship("Fixture", back_populates="league", lazy="selectin")

    def __repr__(self):
        return f"<League(id={self.id}, name='{self.name_cn}')>"
