from datetime import date
from pydantic import BaseModel


class RecommendRequest(BaseModel):
    role_code: str
    coe: str
    allocation_pct: float = 100.0
    start_date: date | None = None
    duration_weeks: int | None = None
    skills_required: str | None = None
    pipeline_request_id: int | None = None


class ScoreBreakdown(BaseModel):
    skill: float
    competency: float | None
    availability: float
    productivity: float
    total: float
    has_competency: bool


class CandidateResult(BaseModel):
    employee_id: str
    job_name: str | None
    canonical_role: str | None
    location: str | None
    department_name: str | None
    current_allocated_pct: float
    available_pct: float
    category: str          # Available / BestMatch / Stretch
    scores: ScoreBreakdown
    rationale: str | None = None


class RecommendSummary(BaseModel):
    total_evaluated: int
    role_matched: int
    available: int
    best_match: int
    stretch: int
    no_resource: bool
    hire_signal: str | None = None   # populated when no Available/BestMatch candidates exist


class RoleMappingInfo(BaseModel):
    raw_code: str
    canonical_roles: list[str] | None
    is_compound: bool
    always_best_match: bool


class RecommendResponse(BaseModel):
    request: RecommendRequest
    role_info: RoleMappingInfo | None
    candidates: list[CandidateResult]
    summary: RecommendSummary
