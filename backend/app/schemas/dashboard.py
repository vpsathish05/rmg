from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    on_bench: int
    partially_available: int
    fully_allocated: int
    active_projects: int
    red_projects: int
    amber_projects: int
    pipeline_requests: int
    high_probability_pipeline: int  # probability_weight >= 0.7
