from datetime import date
from pydantic import BaseModel


class EmployeeAllocationDetail(BaseModel):
    project_id: str
    client_id: str | None
    allocation_pct: float | None
    resourcing_status: str | None
    start_date: date | None
    end_date: date | None
    is_open_ended: bool
    days_remaining: int | None

    model_config = {"from_attributes": True}


class EmployeeAvailability(BaseModel):
    employee_id: str
    job_name: str | None
    canonical_role: str | None
    department_name: str | None
    location: str | None
    allocated_pct: float
    available_pct: float
    allocation_status: str            # On Bench / Available / Partial / Allocated / Over-allocated
    billability: str | None = None    # BILLABLE / SHADOW / UNBILLED — worst case across active allocs
    nearest_end_date: date | None = None  # earliest allocation end date

    model_config = {"from_attributes": True}
