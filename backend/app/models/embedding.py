from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base


class ProjectEmbedding(Base):
    __tablename__ = "project_embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=True)
    summary_text = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
