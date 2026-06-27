from sqlalchemy import ARRAY, Boolean, Column, Date, Integer, Numeric, SmallInteger, String, Text
from app.database import Base


class PipelineRequest(Base):
    __tablename__ = "pipeline_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster = Column(SmallInteger, nullable=True)
    client_name = Column(String, nullable=True)
    client_priority = Column(String, nullable=True)
    deal_stage = Column(String, nullable=True)
    solution = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    status = Column(String, nullable=True)
    sow_signed = Column(Boolean, nullable=True)
    probability_weight = Column(Numeric(3, 2), nullable=True)
    role_code_raw = Column(String, nullable=True)
    canonical_roles = Column(ARRAY(String), nullable=True)
    always_best_match = Column(Boolean, default=False)
    allocation_pct = Column(Numeric(5, 2), nullable=True)
    required_skills = Column(Text, nullable=True)
    skillset_match = Column(String, nullable=True)
    likely_start_date = Column(Date, nullable=True)
    start_date_confirmed = Column(Boolean, default=False)
    duration_weeks = Column(SmallInteger, nullable=True)
    request_type = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    request_received = Column(Date, nullable=True)
    original_requested_start_date = Column(Date, nullable=True)
    em_name = Column(String, nullable=True)
