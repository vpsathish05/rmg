from sqlalchemy import Boolean, Column, Integer, SmallInteger, String, Text
from app.database import Base


class EmployeeCompetency(Base):
    __tablename__ = "employee_competencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    role_group = Column(String, nullable=True)  # sheet name: Solutions Enabler, Solutions Consultant, SSE
    coe_dep = Column(String, nullable=True)
    dimension_index = Column(SmallInteger, nullable=True)  # 1-5
    dimension_text = Column(Text, nullable=True)
    is_demonstrated = Column(Boolean, nullable=True)
    score = Column(SmallInteger, nullable=True)
