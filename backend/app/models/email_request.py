from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.database import Base


class EmailRequest(Base):
    __tablename__ = "email_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    outlook_message_id = Column(String, unique=True, nullable=True)
    source_email = Column(String, nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    request_type = Column(String, nullable=True)  # EXTEND / CHANGE
    raw_body = Column(Text, nullable=True)
    parsed_json = Column(JSONB, nullable=True)
    status = Column(String, default="PENDING")  # PENDING / PARSED / ERROR
    pipeline_request_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
