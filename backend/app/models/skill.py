from sqlalchemy import Boolean, Column, Integer, SmallInteger, String
from app.database import Base


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    coe = Column(String, nullable=True)
    coe_skill = Column(String, nullable=True)
    skill_category = Column(String, nullable=True)
    sub_skill = Column(String, nullable=True)
    experience_band = Column(String, nullable=True)
    score = Column(SmallInteger, nullable=True)  # NULL when unassessed
    is_assessed = Column(Boolean, default=False)
