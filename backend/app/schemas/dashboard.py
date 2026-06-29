from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    on_bench: int
    partially_available: int
    fully_allocated: int
    # Allocation Health breakdown
    billable_count: int = 0          # BILLABLE allocations, total ≤ 100%
    unbillable_count: int = 0        # Allocated but NOT billable, or shadow (timesheet but no allocation)
    over_allocated_count: int = 0    # Total allocation > 100% across projects
    # Revenue leakage
    unbillable_leakage_monthly: float = 0.0   # £ monthly revenue lost to unbillable allocations
    overalloc_leakage_monthly: float = 0.0    # £ monthly revenue at risk from over-allocation
    active_projects: int
    red_projects: int
    amber_projects: int
    pipeline_requests: int
    high_probability_pipeline: int  # probability_weight >= 0.7
