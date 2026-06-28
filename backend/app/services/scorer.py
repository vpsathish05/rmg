"""
Core scoring engine for Phase 2 — Resource Recommendation.

Formula:
  With competency data:    total = skill*0.40 + comp*0.25 + avail*0.25 + prod*0.10
  Without competency data: total = skill*0.65 + avail*0.25 + prod*0.10

All sub-scores are 0.0–1.0.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import text

# Map canonical_role → competency role_group (only 3 exist in data)
COMP_ROLE_GROUP: dict[str, str] = {
    "Solutions Enabler":        "Solutions Enabler",
    "Solutions Consultant":     "Solutions Consultant",
    "Senior Solution Consultant": "Solutions Consultant",
    "Senior Software Engineer": "Senior Software Engineer",
}

WEIGHTS_WITH_COMP    = dict(skill=0.40, comp=0.25, avail=0.25, prod=0.10)
WEIGHTS_WITHOUT_COMP = dict(skill=0.65, comp=0.00, avail=0.25, prod=0.10)

SKILL_NEUTRAL = 0.15  # score used when employee has skills data but NOT for the requested COE


@dataclass
class CandidateScore:
    employee_id: str
    job_name: str | None
    canonical_role: str | None
    location: str | None
    department_name: str | None
    current_allocated_pct: float
    available_pct: float
    skill_score: float
    comp_score: float | None
    avail_score: float
    prod_score: float
    total_score: float
    has_competency: bool
    category: str   # Available / BestMatch / Stretch
    semantic_score: float | None = field(default=None)
    rationale: str | None = field(default=None)


def _normalize_coe(coe: str) -> str:
    return coe.strip().lower()


def score_all(
    db: Session,
    canonical_roles: list[str] | None,
    always_best_match: bool,
    coe: str,
    requested_alloc_pct: float,
    semantic_scores: dict[str, float] | None = None,
) -> list[CandidateScore]:
    """Score every eligible employee and return sorted list (best first)."""

    # ── 1. Candidate pool ────────────────────────────────────────────────────
    if always_best_match or not canonical_roles:
        # Include everyone; score differentiates
        emp_rows = db.execute(text("""
            SELECT employee_id, job_name, canonical_role, location, department_name
            FROM employees
            WHERE account_status = true
              AND is_active_version = true
              AND date_of_resignation IS NULL
              AND job_name IS NOT NULL
        """)).fetchall()
    else:
        emp_rows = db.execute(text("""
            SELECT employee_id, job_name, canonical_role, location, department_name
            FROM employees
            WHERE account_status = true
              AND is_active_version = true
              AND date_of_resignation IS NULL
              AND job_name IS NOT NULL
              AND canonical_role = ANY(:roles)
        """), {"roles": canonical_roles}).fetchall()

        # Fallback: if role-filtered pool is empty, widen to all employees
        if not emp_rows:
            emp_rows = db.execute(text("""
                SELECT employee_id, job_name, canonical_role, location, department_name
                FROM employees
                WHERE account_status = true
                  AND is_active_version = true
                  AND date_of_resignation IS NULL
                  AND job_name IS NOT NULL
            """)).fetchall()

    if not emp_rows:
        return []

    emp_ids = [r.employee_id for r in emp_rows]

    # ── 2. Batch: active allocations ─────────────────────────────────────────
    alloc_rows = db.execute(text("""
        SELECT employee_id, COALESCE(SUM(allocation_pct), 0) AS total_pct
        FROM allocations
        WHERE employee_id = ANY(:ids)
          AND is_active = true
          AND is_active_version = true
          AND (end_date IS NULL OR end_date >= CURRENT_DATE)
        GROUP BY employee_id
    """), {"ids": emp_ids}).fetchall()
    alloc_cache: dict[str, float] = {r.employee_id: float(r.total_pct) for r in alloc_rows}

    # ── 3. Batch: skill scores for requested COE ──────────────────────────────
    skill_rows = db.execute(text("""
        SELECT employee_id, score
        FROM employee_skills
        WHERE employee_id = ANY(:ids)
          AND LOWER(coe) = :coe
          AND is_assessed = true
          AND score IS NOT NULL
          AND score > 0
    """), {"ids": emp_ids, "coe": _normalize_coe(coe)}).fetchall()
    skill_cache: dict[str, list[float]] = {}
    for r in skill_rows:
        skill_cache.setdefault(r.employee_id, []).append(float(r.score))

    # Employees who have skills in ANY COE (used for SKILL_NEUTRAL fallback)
    any_skill_rows = db.execute(text("""
        SELECT DISTINCT employee_id FROM employee_skills
        WHERE employee_id = ANY(:ids) AND is_assessed = true AND score IS NOT NULL
    """), {"ids": emp_ids}).fetchall()
    has_any_skill: set[str] = {r.employee_id for r in any_skill_rows}

    # ── 4. Batch: competency scores (only relevant role groups) ───────────────
    # Collect which employees have which role_group
    role_group_by_emp: dict[str, str] = {}
    for r in emp_rows:
        rg = COMP_ROLE_GROUP.get(r.canonical_role or "")
        if rg:
            role_group_by_emp[r.employee_id] = rg

    comp_cache: dict[str, list[float]] = {}
    if role_group_by_emp:
        comp_rows = db.execute(text("""
            SELECT employee_id, score
            FROM employee_competencies
            WHERE employee_id = ANY(:ids)
              AND score IS NOT NULL
        """), {"ids": list(role_group_by_emp.keys())}).fetchall()
        for r in comp_rows:
            comp_cache.setdefault(r.employee_id, []).append(float(r.score))

    # ── 5. Batch: productivity (approved hours last 8 weeks) ─────────────────
    prod_rows = db.execute(text("""
        SELECT employee_id, COALESCE(SUM(hours), 0) AS approved_hours
        FROM timesheets
        WHERE employee_id = ANY(:ids)
          AND status = 'APPROVED'
          AND date >= CURRENT_DATE - INTERVAL '56 days'
        GROUP BY employee_id
    """), {"ids": emp_ids}).fetchall()
    prod_cache: dict[str, float] = {r.employee_id: float(r.approved_hours) for r in prod_rows}

    # ── 6. Score each candidate ───────────────────────────────────────────────
    results: list[CandidateScore] = []
    expected_hours = 8 * 40  # 8 weeks × 40h

    for r in emp_rows:
        eid = r.employee_id

        # Skill (SKILL_NEUTRAL when employee has skills data but not for this COE)
        scores = skill_cache.get(eid, [])
        if scores:
            coe_skill_score = sum(scores) / len(scores) / 5.0
        elif eid in has_any_skill:
            coe_skill_score = SKILL_NEUTRAL   # assessed in other COEs, not this one
        else:
            coe_skill_score = 0.0             # never assessed

        # Blend with semantic score if available (50/50)
        sem = semantic_scores.get(eid) if semantic_scores else None
        if sem is not None and coe_skill_score > 0:
            skill_score = 0.5 * coe_skill_score + 0.5 * sem
        elif sem is not None:
            skill_score = sem
        else:
            skill_score = coe_skill_score

        # Competency
        comp_scores = comp_cache.get(eid, [])
        comp_score: float | None = None
        if comp_scores:
            comp_score = sum(comp_scores) / len(comp_scores) / 4.0

        # Availability
        allocated = alloc_cache.get(eid, 0.0)
        available = max(0.0, 100.0 - allocated)
        avail_score = available / 100.0

        # Productivity
        hours = prod_cache.get(eid, 0.0)
        prod_score = min(1.0, hours / expected_hours)

        # Total
        has_comp = comp_score is not None
        if has_comp:
            total = (skill_score * 0.40 + comp_score * 0.25  # type: ignore[operator]
                     + avail_score * 0.25 + prod_score * 0.10)
        else:
            total = skill_score * 0.65 + avail_score * 0.25 + prod_score * 0.10

        # Category — availability drives the primary split; score ranks within each group
        if available >= requested_alloc_pct:
            category = "Available"
        elif total >= 0.40:
            category = "BestMatch"   # allocated but has measurable fit — discuss reallocation
        else:
            category = "Stretch"     # allocated AND weak fit

        results.append(CandidateScore(
            employee_id=eid,
            job_name=r.job_name,
            canonical_role=r.canonical_role,
            location=r.location,
            department_name=r.department_name,
            current_allocated_pct=round(allocated, 1),
            available_pct=round(available, 1),
            skill_score=round(skill_score, 3),
            comp_score=round(comp_score, 3) if comp_score is not None else None,
            avail_score=round(avail_score, 3),
            prod_score=round(prod_score, 3),
            total_score=round(total, 3),
            has_competency=has_comp,
            category=category,
            semantic_score=round(sem, 3) if sem is not None else None,
        ))

    results.sort(key=lambda c: c.total_score, reverse=True)
    return results
