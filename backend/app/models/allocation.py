from sqlalchemy import Boolean, Column, Date, Numeric, String
from app.database import Base


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(String, primary_key=True)  # project_rolebased_user_id
    project_id = Column(String, nullable=False)
    employee_id = Column(String, nullable=True)
    resourcing_status = Column(String, nullable=True)
    allocation_pct = Column(Numeric(5, 2), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_open_ended = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    is_active_version = Column(Boolean, default=True)
