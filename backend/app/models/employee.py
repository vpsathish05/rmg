from sqlalchemy import Boolean, Column, Date, String
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String, primary_key=True)
    location = Column(String)
    date_of_join = Column(Date)
    date_of_resignation = Column(Date, nullable=True)
    job_name = Column(String)
    department_name = Column(String)
    manager_id = Column(String, nullable=True)
    account_status = Column(Boolean, default=False)
    canonical_role = Column(String, nullable=True)
    hierarchy_region = Column(String, nullable=True)  # 'IN' or 'UK_US'
    is_active_version = Column(Boolean, default=True)
