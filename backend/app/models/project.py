from sqlalchemy import Boolean, Column, Date, String
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True)
    project_key = Column(String, unique=True, nullable=True)
    client_id = Column(String, nullable=False)
    project_start_date = Column(Date, nullable=True)
    project_end_date = Column(Date, nullable=True)
    type_of_project = Column(String, nullable=True)
    project_status = Column(String, nullable=True)
    proposition_coe = Column(String, nullable=True)
    reporter_id = Column(String, nullable=True)
    approver_id = Column(String, nullable=True)
    is_active_version = Column(Boolean, default=True)


class ProjectCOE(Base):
    __tablename__ = "project_coes"

    project_id = Column(String, primary_key=True)
    coe = Column(String, primary_key=True)
