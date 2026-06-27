from sqlalchemy import Column, DateTime, String
from app.database import Base


class WeeklyStatus(Base):
    __tablename__ = "weekly_status"

    id = Column(String, primary_key=True)  # wsr_key
    wsr_id = Column(String, unique=True, nullable=True)
    project_id = Column(String, nullable=True)
    week_start = Column(String, nullable=True)
    week_end = Column(String, nullable=True)
    scope_status = Column(String, nullable=True)
    schedule_status = Column(String, nullable=True)
    quality_status = Column(String, nullable=True)
    csat_status = Column(String, nullable=True)
    team_status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
