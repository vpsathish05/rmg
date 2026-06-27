from sqlalchemy import ARRAY, Boolean, Column, String, Text
from app.database import Base


class RoleMapping(Base):
    __tablename__ = "role_mapping"

    raw_code = Column(String, primary_key=True)
    canonical_roles = Column(ARRAY(String), nullable=True)
    is_compound = Column(Boolean, default=False)
    always_best_match = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
