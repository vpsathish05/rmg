from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.schemas.recommend import (
    RecommendRequest, RecommendResponse, CandidateResult,
    ScoreBreakdown, RecommendSummary, RoleMappingInfo,
)
from app.services import scorer as scoring_svc
from app.services.llm import generate_rationales_batch

router = APIRouter()


@router.get("/coes")
def list_coes(db: Session = Depends(get_db)):
    """Return distinct COEs from skill data (for form dropdown)."""
    rows = db.execute(text(
        "SELECT DISTINCT INITCAP(coe) AS coe FROM employee_skills WHERE coe IS NOT NULL ORDER BY 1"
    )).fetchall()
    return [r.coe for r in rows]


@router.get("/role-codes")
def list_role_codes(db: Session = Depends(get_db)):
    """Return all role codes from role_mapping (excluding ignored ones)."""
    rows = db.execute(text(
        "SELECT raw_code, canonical_roles, always_best_match FROM role_mapping "
        "WHERE canonical_roles IS NOT NULL ORDER BY raw_code"
    )).fetchall()
    return [
        {"raw_code": r.raw_code, "canonical_roles": r.canonical_roles,
         "always_best_match": r.always_best_match}
        for r in rows
    ]


@router.post("", response_model=RecommendResponse)
async def recommend(
    req: RecommendRequest,
    with_rationale: bool = Query(True, description="Generate OpenAI rationale for top 10"),
    db: Session = Depends(get_db),
):
    # ── Resolve role code → canonical roles ──────────────────────────────────
    rm_row = db.execute(text(
        "SELECT raw_code, canonical_roles, is_compound, always_best_match "
        "FROM role_mapping WHERE raw_code = :code"
    ), {"code": req.role_code}).fetchone()

    canonical_roles: list[str] | None = None
    always_best_match = False
    role_info: RoleMappingInfo | None = None

    if rm_row:
        canonical_roles = rm_row.canonical_roles
        always_best_match = rm_row.always_best_match
        role_info = RoleMappingInfo(
            raw_code=rm_row.raw_code,
            canonical_roles=rm_row.canonical_roles,
            is_compound=rm_row.is_compound,
            always_best_match=rm_row.always_best_match,
        )

    # ── Score all eligible candidates ─────────────────────────────────────────
    scored = scoring_svc.score_all(
        db=db,
        canonical_roles=canonical_roles,
        always_best_match=always_best_match,
        coe=req.coe,
        requested_alloc_pct=req.allocation_pct,
    )

    # ── Optionally add OpenAI rationale for top 10 ───────────────────────────
    if with_rationale and scored:
        scored = await generate_rationales_batch(scored, req, top_n=10)

    # ── Build response ────────────────────────────────────────────────────────
    candidates = [
        CandidateResult(
            employee_id=c.employee_id,
            job_name=c.job_name,
            canonical_role=c.canonical_role,
            location=c.location,
            department_name=c.department_name,
            current_allocated_pct=c.current_allocated_pct,
            available_pct=c.available_pct,
            category=c.category,
            scores=ScoreBreakdown(
                skill=c.skill_score,
                competency=c.comp_score,
                availability=c.avail_score,
                productivity=c.prod_score,
                total=c.total_score,
                has_competency=c.has_competency,
            ),
            rationale=c.rationale,
        )
        for c in scored
    ]

    avail = sum(1 for c in scored if c.category == "Available")
    bm    = sum(1 for c in scored if c.category == "BestMatch")
    st    = sum(1 for c in scored if c.category == "Stretch")

    no_resource = (avail + bm) == 0
    hire_signal: str | None = None
    if no_resource:
        hire_signal = (
            f"No suitable internal candidate found for role '{req.role_code}' in {req.coe}. "
            f"{len(scored)} employees evaluated — all are at capacity or lack verified {req.coe} skills. "
            f"Consider external hire or redeployment from an adjacent COE."
        )

    summary = RecommendSummary(
        total_evaluated=len(scored),
        role_matched=len(scored),
        available=avail,
        best_match=bm,
        stretch=st,
        no_resource=no_resource,
        hire_signal=hire_signal,
    )

    return RecommendResponse(
        request=req,
        role_info=role_info,
        candidates=candidates,
        summary=summary,
    )
