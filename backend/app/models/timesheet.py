from sqlalchemy import Column, Date, Numeric, String
from app.database import Base


class Timesheet(Base):
    __tablename__ = "timesheets"

    surrogate_key = Column(String, primary_key=True)
    employee_id = Column(String, nullable=True)
    timesheet_id = Column(String, nullable=True)
    manager_id = Column(String, nullable=True)
    project_id = Column(String, nullable=True)
    project_task_id = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    hours = Column(Numeric(6, 2), nullable=True)
    status = Column(String, nullable=True)
    submitted_on = Column(Date, nullable=True)
    created_at = Column(Date, nullable=True)
    updated_at = Column(Date, nullable=True)
