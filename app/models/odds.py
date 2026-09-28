"""
Odds model - represents betting odds for fixtures.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Index, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class OddsType(str, PyEnum):
    """Betting odds type enum."""
    SP_WDW = "SP_WDW"           # 胜平负 (Win/Draw/Loss)
    SP_HDP = "SP_HDP"           # 让球胜平负 (Handicap Win/Draw/Loss)
    SP_SCORE = "SP_SCORE"       # 比分 (Correct Score)
    SP_TOTAL = "SP_TOTAL"       # 总进球 (Total Goals)
    SP_HALF = "SP_HALF"         # 半全场 (Half-time/Full-time)
    SP_BQ = "SP_BQ"             # 单双 (Big/Small or Odd/Even)


class Odds(Base):
    """Betting odds model."""
    __tablename__ = "odds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False, index=True)
    odds_type = Column(Enum(OddsType), nullable=False, index=True, comment="Odds type")
    option_code = Column(String(20), nullable=False, comment="Option code (e.g., 'H', 'D', 'A', '1:0')")
    option_name = Column(String(50), nullable=True, comment="Option name in Chinese")
    odds_value = Column(Float, nullable=False, comment="Odds value")
    handicap = Column(String(20), nullable=True, comment="Handicap value (if applicable)")
    is_stopped = Column(Integer, default=0, nullable=False, comment="Is betting stopped: 0=no, 1=yes")
    is_recommended = Column(Integer, default=0, nullable=False, comment="Is AI recommended: 0=no, 1=yes")
    confidence = Column(Float, nullable=True, comment="AI confidence score (0-1)")
    source = Column(String(50), nullable=True, comment="Odds source")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    fixture = relationship("Fixture", back_populates="odds")

    # Composite indexes
    __table_args__ = (
        Index("idx_odds_fixture_type", "fixture_id", "odds_type"),
        Index("idx_odds_fixture_option", "fixture_id", "odds_type", "option_code", unique=True),
    )

    def __repr__(self):
        return f"<Odds(id={self.id}, type={self.odds_type}, option={self.option_code}, value={self.odds_value})>"
