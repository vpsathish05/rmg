from datetime import date
from pydantic import BaseModel


class ProjectHealth(BaseModel):
    project_id: str
    client_id: str
    project_status: str | None
    proposition_coe: str | None
    project_start_date: date | None
    project_end_date: date | None
    scope_status: str | None
    schedule_status: str | None
    quality_status: str | None
    csat_status: str | None
    team_status: str | None
    overall_health: str  # RED / AMBER / GREEN / NO_COLOR
    week_end: date | None

    model_config = {"from_attributes": True}
