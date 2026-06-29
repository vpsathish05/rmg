"""
RMG Engine API - powers the main 3-panel screen.

Endpoints:
  GET  /api/rmg/pipeline          - upcoming projects grouped by client (with roles)
  GET  /api/rmg/extensions        - projects with allocations extended beyond end date
  GET  /api/rmg/email-requests    - email_requests (EXTEND + CHANGE) for Cards 2 & 3
  POST /api/rmg/recommend-role    - inline recommendation for a specific pipeline role
  POST /api/rmg/kb/build          - trigger KB (re)build
  GET  /api/rmg/kb/status         - KB stats
"""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.database import get_db
from app.config import settings
from app.services import scorer as scoring_svc
from app.services.llm import generate_rationales_batch
from app.services.kb import search_employee_proofs, compute_semantic_skill_scores

router = APIRouter()

# ── Priority sort order for account type ──────────────────────────────────────
_PRIORITY_ORDER = {"Gold": 0, "Silver": 1, "Bronze": 2, "Other": 3}


# ─────────────────────────────────────────────────────────────────────────────
# Card 1 - Upcoming Projects
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/pipeline")
def get_pipeline(db: Session = Depends(get_db)):
    """Return pipeline requests grouped by client, sorted by priority then start date."""
    rows = db.execute(text("""
        SELECT
            client_name,
            MAX(client_priority) AS client_priority,
            MAX(deal_stage)      AS deal_stage,
            MAX(solution)        AS solution,
            MIN(likely_start_date) AS likely_start_date,
            MAX(probability_weight) AS probability_weight,
            BOOL_OR(COALESCE(sow_signed, false)) AS sow_signed,
            MAX(em_name)         AS em_name,
            COUNT(*)             AS role_count,
            JSON_AGG(JSON_BUILD_OBJECT(
                'id',              id,
                'role_code_raw',   role_code_raw,
                'canonical_roles', canonical_roles,
                'allocation_pct',  allocation_pct,
                'duration_weeks',  duration_weeks,
                'required_skills', NULLIF(required_skills, 'nan'),
                'status',          status,
                'comments',        NULLIF(comments, 'nan'),
                'resourced_employee_id', resourced_employee_id
            ) ORDER BY id) AS roles
        FROM pipeline_requests
        WHERE client_name IS NOT NULL
        GROUP BY client_name
        ORDER BY MAX(probability_weight) DESC NULLS LAST,
                 MIN(likely_start_date) ASC NULLS LAST
    """)).fetchall()

    projects = []
    for r in rows:
        projects.append({
            "client_name":        r.client_name,
            "client_priority":    r.client_priority,
            "deal_stage":         r.deal_stage,
            "solution":           r.solution,
            "likely_start_date":  r.likely_start_date.isoformat() if r.likely_start_date else None,
            "probability_weight": float(r.probability_weight) if r.probability_weight else None,
            "sow_signed":         bool(r.sow_signed),
            "em_name":            r.em_name,
            "role_count":         int(r.role_count),
            "roles":              r.roles,
        })

    # Sort by account priority
    projects.sort(key=lambda p: (
        _PRIORITY_ORDER.get(p["client_priority"] or "Other", 3),
        -(sum(1 for r in p["roles"] if r.get("status") == "Not Resourced")),
        p["likely_start_date"] or "9999",
    ))
    return projects


# ─────────────────────────────────────────────────────────────────────────────
# Card 2 - Extensions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/extensions")
def get_extensions(db: Session = Depends(get_db)):
    """Projects where at least one allocation end_date > project_end_date."""
    rows = db.execute(text("""
        SELECT
            p.project_id,
            p.client_id,
            p.proposition_coe,
            p.project_end_date,
            MAX(a.end_date) AS max_alloc_end_date,
            (MAX(a.end_date) - p.project_end_date) AS days_extended,
            COUNT(DISTINCT a.employee_id) AS headcount,
            STRING_AGG(DISTINCT UPPER(a.resourcing_status), ', ') AS resourcing_statuses
        FROM allocations a
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        WHERE a.is_active = true
          AND a.is_active_version = true
          AND a.end_date IS NOT NULL
          AND p.project_end_date IS NOT NULL
          AND a.end_date > p.project_end_date
        GROUP BY p.project_id, p.client_id, p.proposition_coe, p.project_end_date
        ORDER BY days_extended DESC
        LIMIT 100
    """)).fetchall()

    # Also pull EXTEND email requests
    email_rows = db.execute(text("""
        SELECT id::text, source_email, received_at, parsed_json, status, created_at
        FROM email_requests
        WHERE request_type = 'EXTEND'
        ORDER BY received_at DESC
        LIMIT 20
    """)).fetchall()

    return {
        "allocation_extensions": [
            {
                "project_id":          r.project_id,
                "client_id":           r.client_id,
                "proposition_coe":     r.proposition_coe,
                "project_end_date":    r.project_end_date.isoformat() if r.project_end_date else None,
                "max_alloc_end_date":  r.max_alloc_end_date.isoformat() if r.max_alloc_end_date else None,
                "days_extended":       int(r.days_extended),
                "headcount":           int(r.headcount),
                "resourcing_statuses": r.resourcing_statuses,
            }
            for r in rows
        ],
        "email_extensions": [
            {
                "id":           r.id,
                "source_email": r.source_email,
                "received_at":  r.received_at.isoformat() if r.received_at else None,
                "parsed_json":  r.parsed_json,
                "status":       r.status,
            }
            for r in email_rows
        ],
    }


@router.get("/extensions/needs")
def get_extension_needs(db: Session = Depends(get_db)):
    """Projects where resources are ending before the project ends - need replacements."""
    rows = db.execute(text("""
        SELECT
            p.project_id, p.client_id, p.proposition_coe,
            p.project_end_date, p.project_status,
            a.employee_id, e.job_name, e.canonical_role,
            a.end_date AS alloc_end_date,
            a.allocation_pct,
            a.resourcing_status,
            (p.project_end_date - a.end_date) AS days_gap
        FROM allocations a
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        WHERE a.is_active = true
          AND a.is_active_version = true
          AND a.end_date IS NOT NULL
          AND p.project_end_date IS NOT NULL
          AND a.end_date < p.project_end_date
          AND a.end_date >= CURRENT_DATE - INTERVAL '30 days'
          AND UPPER(p.project_status) = 'ACTIVE'
        ORDER BY p.client_id, p.project_id, a.end_date
    """)).fetchall()

    # Group by project
    from collections import defaultdict
    projects: dict = {}
    for r in rows:
        key = r.project_id
        if key not in projects:
            projects[key] = {
                "project_id": r.project_id,
                "client_id": r.client_id,
                "proposition_coe": r.proposition_coe,
                "project_end_date": r.project_end_date.isoformat() if r.project_end_date else None,
                "project_status": r.project_status,
                "leaving_resources": [],
            }
        projects[key]["leaving_resources"].append({
            "employee_id": r.employee_id,
            "job_name": r.job_name,
            "canonical_role": r.canonical_role,
            "alloc_end_date": r.alloc_end_date.isoformat() if r.alloc_end_date else None,
            "allocation_pct": float(r.allocation_pct) if r.allocation_pct else None,
            "resourcing_status": r.resourcing_status,
            "days_gap": int(r.days_gap),
        })

    return list(projects.values())


# ─────────────────────────────────────────────────────────────────────────────
# Card 3 - Change Requests
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/email-requests")
def get_email_requests(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id::text, source_email, received_at, request_type,
               parsed_json, status, created_at
        FROM email_requests
        ORDER BY received_at DESC NULLS LAST
        LIMIT 50
    """)).fetchall()
    return [
        {
            "id":           r.id,
            "source_email": r.source_email,
            "received_at":  r.received_at.isoformat() if r.received_at else None,
            "request_type": r.request_type,
            "parsed_json":  r.parsed_json,
            "status":       r.status,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Inline Recommendation for a Role
# ─────────────────────────────────────────────────────────────────────────────

class RoleRecommendRequest(BaseModel):
    role_code: str
    canonical_roles: list[str] | None = None
    always_best_match: bool = False
    coe: str
    allocation_pct: float = 100.0
    required_skills: str | None = None
    with_rationale: bool = True
    with_kb_proof: bool = True


@router.post("/recommend-role")
async def recommend_for_role(
    req: RoleRecommendRequest,
    db: Session = Depends(get_db),
):
    """Score candidates for a specific pipeline role. Returns Available/BestMatch/NoResource."""
    # Compute semantic skill scores if required_skills provided
    semantic_scores = None
    role_query = f"{req.role_code} {req.coe} {req.required_skills or ''}".strip().replace("nan", "")
    if role_query:
        # Get all candidate IDs first for semantic scoring
        from sqlalchemy import text as sa_text
        all_ids = [r.employee_id for r in db.execute(sa_text(
            "SELECT employee_id FROM employees WHERE account_status=true AND is_active_version=true AND date_of_resignation IS NULL"
        )).fetchall()]
        semantic_scores = await compute_semantic_skill_scores(db, role_query, all_ids)

    scored = scoring_svc.score_all(
        db=db,
        canonical_roles=req.canonical_roles,
        always_best_match=req.always_best_match,
        coe=req.coe,
        requested_alloc_pct=req.allocation_pct,
        semantic_scores=semantic_scores,
    )

    # Rationale for top 10
    if req.with_rationale and scored:
        from app.schemas.recommend import RecommendRequest
        from datetime import date
        fake_req = RecommendRequest(
            role_code=req.role_code,
            coe=req.coe,
            allocation_pct=req.allocation_pct,
            skills_required=req.required_skills,
        )
        scored = await generate_rationales_batch(scored, fake_req, top_n=10)

    # KB proofs for top 6 (Available + BestMatch top 3 each)
    kb_active = False
    kb_proofs: dict[str, list] = {}
    if req.with_kb_proof:
        query_text = f"{req.role_code} {req.coe} {req.required_skills or ''}".strip().replace("nan", "")
        top_candidates = [c for c in scored if c.category in ("Available", "BestMatch")][:6]
        proof_tasks = [
            search_employee_proofs(db, c.employee_id, query_text)
            for c in top_candidates
        ]
        proof_results = await asyncio.gather(*proof_tasks, return_exceptions=True)
        for c, proofs in zip(top_candidates, proof_results):
            if isinstance(proofs, list) and proofs:
                kb_proofs[c.employee_id] = proofs
                kb_active = True

    # Split into categories (top 3 each)
    available  = [c for c in scored if c.category == "Available"][:3]
    best_match = [c for c in scored if c.category == "BestMatch"][:3]
    no_resource = len(available) + len(best_match) == 0

    def _fmt(c):
        return {
            "employee_id":          c.employee_id,
            "job_name":             c.job_name,
            "canonical_role":       c.canonical_role,
            "location":             c.location,
            "department_name":      c.department_name,
            "current_allocated_pct": c.current_allocated_pct,
            "available_pct":        c.available_pct,
            "category":             c.category,
            "total_score":          c.total_score,
            "skill_score":          c.skill_score,
            "comp_score":           c.comp_score,
            "avail_score":          c.avail_score,
            "prod_score":           c.prod_score,
            "has_competency":       c.has_competency,
            "semantic_score":       c.semantic_score,
            "rationale":            c.rationale,
            "kb_proof":             kb_proofs.get(c.employee_id, []),
        }

    hire_signal = None
    if no_resource:
        from app.services.llm import generate_smart_hire_signal
        top_stretch = [c for c in scored if c.category == "Stretch"][:3]
        from app.schemas.recommend import RecommendRequest as RR
        hire_req = RR(role_code=req.role_code, coe=req.coe, allocation_pct=req.allocation_pct, skills_required=req.required_skills)
        hire_signal = await generate_smart_hire_signal(hire_req, len(scored), top_stretch)

    return {
        "available":   [_fmt(c) for c in available],
        "best_match":  [_fmt(c) for c in best_match],
        "no_resource": no_resource,
        "hire_signal": hire_signal,
        "kb_active":   kb_active,
        "total_evaluated": len(scored),
    }


# ─────────────────────────────────────────────────────────────────────────────
# KB management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/kb/build")
async def build_kb(db: Session = Depends(get_db)):
    """Trigger KB rebuild - embeds all projects. Takes 2-5 minutes."""
    from app.services.kb import build_all
    n = await build_all(db)
    return {"message": f"KB built: {n} project embeddings created."}


@router.get("/kb/status")
def kb_status(db: Session = Depends(get_db)):
    count = db.execute(text("SELECT COUNT(*) FROM project_embeddings")).scalar()
    return {"embeddings": int(count), "kb_active": int(count) > 0}


# ─────────────────────────────────────────────────────────────────────────────
# Auto-COE detection
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/auto-coe")
async def get_auto_coe(
    canonical_roles: list[str] = Query(default=[]),
    role_code: str = Query(default=""),
    required_skills: str = Query(default=""),
    db: Session = Depends(get_db),
):
    """Find the most common assessed COE for employees with the given canonical roles."""
    if not canonical_roles:
        return {"coe": None}

    row = db.execute(text("""
        SELECT INITCAP(TRIM(es.coe)) AS coe, COUNT(*) AS cnt
        FROM employee_skills es
        JOIN employees e ON e.employee_id = es.employee_id
            AND e.is_active_version = true
            AND e.canonical_role = ANY(:roles)
        WHERE es.is_assessed = true
          AND es.score IS NOT NULL
          AND es.coe IS NOT NULL
          AND TRIM(es.coe) != ''
        GROUP BY TRIM(es.coe)
        ORDER BY cnt DESC
        LIMIT 1
    """), {"roles": canonical_roles}).fetchone()

    if row:
        return {"coe": row.coe}

    # Fallback: most common COE across all employees
    fallback = db.execute(text("""
        SELECT INITCAP(TRIM(coe)) AS coe, COUNT(*) AS cnt
        FROM employee_skills
        WHERE is_assessed = true AND score IS NOT NULL
          AND coe IS NOT NULL AND TRIM(coe) != ''
        GROUP BY TRIM(coe)
        ORDER BY cnt DESC
        LIMIT 1
    """)).fetchone()

    if fallback:
        return {"coe": fallback.coe}

    # LLM fallback
    available_rows = db.execute(text("""
        SELECT DISTINCT INITCAP(TRIM(coe)) AS coe FROM employee_skills
        WHERE is_assessed = true AND coe IS NOT NULL AND TRIM(coe) != ''
    """)).fetchall()
    available = [r.coe for r in available_rows]
    if available:
        from app.services.llm import get_client
        try:
            coe_list = ", ".join(available)
            resp = await get_client().chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": f"Given COEs: [{coe_list}]. Which best matches role '{role_code}' ({', '.join(canonical_roles)}) with skills '{required_skills}'? Reply ONLY the COE name."}],
                max_tokens=20, temperature=0,
            )
            answer = resp.choices[0].message.content.strip()
            for coe in available:
                if coe.lower() == answer.lower():
                    return {"coe": coe}
        except Exception:
            pass

    return {"coe": available[0] if available else None}


# ─────────────────────────────────────────────────────────────────────────────
# Pre-computed recommendation cache
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/recommendations")
def get_recommendations(db: Session = Depends(get_db)):
    """
    Return all pre-computed role recommendations keyed by pipeline_role_id.
    These are computed nightly at 2am IST and stored in role_recommendations.
    """
    rows = db.execute(text("""
        SELECT pipeline_role_id, coe, available, best_match, no_resource,
               hire_signal, kb_active, total_evaluated, computed_at, status
        FROM role_recommendations
        WHERE status = 'done'
    """)).fetchall()

    return {
        str(r.pipeline_role_id): {
            "coe":              r.coe,
            "available":        r.available,
            "best_match":       r.best_match,
            "no_resource":      r.no_resource,
            "hire_signal":      r.hire_signal,
            "kb_active":        r.kb_active,
            "total_evaluated":  r.total_evaluated,
            "computed_at":      r.computed_at.isoformat() if r.computed_at else None,
            "status":           r.status,
        }
        for r in rows
    }


@router.get("/recommendations/status")
def recommendations_status(db: Session = Depends(get_db)):
    """Return cache freshness metadata and whether a compute is in progress."""
    from app.services import rec_cache as rc

    row = db.execute(text("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'done')    AS done_count,
            COUNT(*) FILTER (WHERE status = 'error')   AS error_count,
            MAX(computed_at)                            AS last_computed_at
        FROM role_recommendations
    """)).fetchone()

    return {
        "done_count":      int(row.done_count or 0),
        "error_count":     int(row.error_count or 0),
        "last_computed_at": row.last_computed_at.isoformat() if row.last_computed_at else None,
        "is_running":      rc.is_running(),
    }


async def _run_compute_bg():
    """Background task: open its own DB session and run compute_all."""
    from app.database import SessionLocal
    from app.services import rec_cache as rc
    import logging
    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        result = await rc.compute_all(db)
        log.info("Manual refresh complete: %s", result)
    except Exception as exc:
        log.error("Manual refresh failed: %s", exc)
    finally:
        db.close()


@router.post("/recommendations/refresh")
async def refresh_recommendations(background_tasks: BackgroundTasks):
    """
    Trigger a full re-compute of all Not Resourced role recommendations.
    Returns immediately - compute runs in the background (~5–10 min).
    """
    from app.services import rec_cache as rc
    if rc.is_running():
        return {"message": "A compute is already in progress - please wait."}
    background_tasks.add_task(_run_compute_bg)
    return {"message": "Recommendation refresh started. Check /api/rmg/recommendations/status for progress."}



# ─────────────────────────────────────────────────────────────────────────────
# Send Recommendation Email
# ─────────────────────────────────────────────────────────────────────────────

class SendRecommendationRequest(BaseModel):
    client_name: str
    to_emails: list[str] = []      # one or more recipients - all editable on the frontend
    to_email: str | None = None    # legacy single-recipient field - kept for backwards compat
    roles: list[dict] = []         # [{role_code, candidates: [{employee_id, job_name, score, category}]}]


@router.post("/send-recommendation")
async def send_recommendation(req: SendRecommendationRequest):
    """Send resource recommendation email via Azure Communication Services."""
    from app.config import settings
    from fastapi.responses import JSONResponse

    # Accept both to_emails (list) and legacy to_email (single string)
    raw = list(req.to_emails) if req.to_emails else []
    if req.to_email and req.to_email.strip():
        raw.append(req.to_email.strip())
    valid_emails = [e.strip() for e in raw if e.strip()]

    if not valid_emails:
        return JSONResponse(status_code=422, content={"status": "error", "message": "At least one recipient email is required."})

    if not settings.acs_connection_string:
        return JSONResponse(status_code=502, content={"status": "error", "message": "Email not configured (ACS connection string missing)"})

    # Build HTML email
    roles_html = ""
    for role in req.roles:
        candidates_html = ""
        for c in role.get("candidates", []):
            cat_color = "#059669" if c.get("category") == "Available" else "#7c3aed"
            candidates_html += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f1f1;font-size:13px">{c.get('employee_id','')}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f1f1;font-size:13px">{c.get('job_name','')}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f1f1;font-size:13px;color:{cat_color};font-weight:600">{c.get('category','')}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #f1f1f1;font-size:13px;font-weight:700">{c.get('score',0)}%</td>
            </tr>"""

        roles_html += f"""
        <div style="margin-bottom:20px">
            <h3 style="margin:0 0 8px;font-size:14px;color:#19105B">{role.get('role_code','Unknown Role')}</h3>
            <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
                <thead>
                    <tr style="background:#f9fafb">
                        <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase">ID</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase">Role</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase">Category</th>
                        <th style="padding:8px 12px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase">Score</th>
                    </tr>
                </thead>
                <tbody>{candidates_html}</tbody>
            </table>
        </div>"""

    body_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
        <div style="background:#19105B;padding:20px 24px;border-radius:12px 12px 0 0">
            <h1 style="margin:0;color:#fff;font-size:18px">Resource Recommendation</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:13px">RMG Engine · Jman Group</p>
        </div>
        <div style="padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px">
            <p style="font-size:14px;color:#374151;margin:0 0 16px">
                Hi,<br><br>
                Here are the AI-recommended resources for <strong>{req.client_name}</strong>:
            </p>
            {roles_html}
            <p style="font-size:12px;color:#9ca3af;margin:16px 0 0;border-top:1px solid #f1f1f1;padding-top:12px">
                Scored by RMG AI Engine - skill match, availability, competency &amp; productivity.
                Please reach out to discuss allocation.
            </p>
        </div>
    </div>"""

    try:
        from azure.communication.email import EmailClient
        client = EmailClient.from_connection_string(settings.acs_connection_string)
        message = {
            "senderAddress": settings.acs_sender_email,
            "recipients": {
                "to": [{"address": e} for e in valid_emails]
            },
            "content": {
                "subject": f"Resource Recommendation - {req.client_name}",
                "html": body_html,
            },
        }
        poller = client.begin_send(message)
        poller.result()
        recipients_str = ", ".join(valid_emails)
        return {"status": "sent", "message": f"Recommendation sent to {recipients_str}"}
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"ACS send_email failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=502, content={"status": "error", "message": str(e)})



# ─────────────────────────────────────────────────────────────────────────────
# Extension Conflicts — Detect scheduling conflicts from project extensions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/extension-conflicts")
def get_extension_conflicts(db: Session = Depends(get_db)):
    """
    Detect employees who have overlapping allocations due to project extensions.

    A conflict occurs when:
    - An employee has an existing BILLABLE allocation on a current project
    - AND a PROPOSED or new BILLABLE allocation on a different project
    - AND the two allocations overlap in time (current project was extended
      past the new project's start date)

    This catches the scenario where someone was proposed for a new project
    because their current project was ending, but then the current project
    got extended — creating a double-booking.
    """
    rows = db.execute(text("""
        WITH current_allocs AS (
            -- Active BILLABLE allocations on current projects (the "extended" side)
            SELECT a.employee_id, a.project_id, a.allocation_pct,
                   a.start_date, a.end_date, a.resourcing_status,
                   p.client_id, p.project_end_date, p.proposition_coe
            FROM allocations a
            JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
            WHERE a.is_active_version = true
              AND a.resourcing_status = 'BILLABLE'
              AND a.end_date >= CURRENT_DATE
              AND a.start_date <= CURRENT_DATE
              AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        ),
        new_allocs AS (
            -- Upcoming PROPOSED or BILLABLE allocations starting in next 30 days
            SELECT a.employee_id, a.project_id, a.allocation_pct,
                   a.start_date, a.end_date, a.resourcing_status,
                   p.client_id, p.proposition_coe
            FROM allocations a
            JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
            WHERE a.is_active_version = true
              AND a.resourcing_status IN ('PROPOSED', 'BILLABLE')
              AND a.start_date > CURRENT_DATE
              AND a.start_date <= CURRENT_DATE + INTERVAL '30 days'
              AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        )
        SELECT
            e.employee_id,
            e.job_name,
            e.canonical_role,
            e.location,
            e.department_name,
            -- Current project (extended)
            c.project_id AS current_project_id,
            c.client_id AS current_client,
            c.allocation_pct AS current_alloc_pct,
            c.start_date AS current_start_date,
            c.end_date AS current_alloc_end,
            c.proposition_coe AS current_coe,
            -- New project (proposed/planned)
            n.project_id AS new_project_id,
            n.client_id AS new_client,
            n.allocation_pct AS new_alloc_pct,
            n.start_date AS new_start_date,
            n.end_date AS new_end_date,
            n.resourcing_status AS new_status,
            n.proposition_coe AS new_coe,
            -- Conflict metrics
            (c.end_date - n.start_date + 1) AS conflict_days,
            (c.allocation_pct + n.allocation_pct) AS total_alloc_pct
        FROM current_allocs c
        JOIN new_allocs n ON n.employee_id = c.employee_id
            AND n.project_id != c.project_id
            AND n.start_date <= c.end_date  -- OVERLAP: new starts before current ends
        JOIN employees e ON e.employee_id = c.employee_id AND e.is_active_version = true
        ORDER BY (c.end_date - n.start_date + 1) DESC, e.job_name
    """)).fetchall()

    conflicts = []
    for r in rows:
        total_pct = float(r.total_alloc_pct or 0)
        # Only flag as conflict if combined allocation > 100%
        if total_pct > 100:
            severity = "critical" if r.conflict_days > 14 else "high" if r.conflict_days > 7 else "medium"
            conflicts.append({
                "employee_id": r.employee_id,
                "job_name": r.job_name,
                "canonical_role": r.canonical_role,
                "location": r.location,
                "department": r.department_name,
                # Current project
                "current_project_id": r.current_project_id,
                "current_client": r.current_client,
                "current_alloc_pct": float(r.current_alloc_pct),
                "current_start_date": r.current_start_date.isoformat() if r.current_start_date else None,
                "current_alloc_end": r.current_alloc_end.isoformat() if r.current_alloc_end else None,
                "current_coe": r.current_coe,
                # New project
                "new_project_id": r.new_project_id,
                "new_client": r.new_client,
                "new_alloc_pct": float(r.new_alloc_pct),
                "new_start_date": r.new_start_date.isoformat() if r.new_start_date else None,
                "new_end_date": r.new_end_date.isoformat() if r.new_end_date else None,
                "new_status": r.new_status,
                "new_coe": r.new_coe,
                # Metrics
                "conflict_days": int(r.conflict_days),
                "total_alloc_pct": total_pct,
                "severity": severity,
            })

    return {
        "conflicts": conflicts,
        "total": len(conflicts),
        "critical": len([c for c in conflicts if c["severity"] == "critical"]),
    }



# ─────────────────────────────────────────────────────────────────────────────
# Extension Confirmations — Email callback + management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/extension-response")
def handle_extension_response(
    token: str = Query(...),
    response: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    One-click callback from extension confirmation email.
    EM clicks a button in the email → lands here.

    response: 'no_extension' | 'extend' | 'partial'
    """
    from fastapi.responses import HTMLResponse

    # Validate token
    row = db.execute(text("""
        SELECT id, project_id, client_id, project_end_date, headcount, team_summary, response AS existing_response
        FROM extension_confirmations
        WHERE token = :token
    """), {"token": token}).fetchone()

    if not row:
        return HTMLResponse(content=_response_page("Invalid or expired link.", error=True), status_code=404)

    if row.existing_response is not None:
        return HTMLResponse(content=_response_page(
            f"Already responded: <strong>{row.existing_response.replace('_', ' ').title()}</strong> for {row.client_id}.",
            error=False
        ))

    valid_responses = ("no_extension", "extend", "partial")
    if response not in valid_responses:
        return HTMLResponse(content=_response_page(f"Invalid response: {response}", error=True), status_code=400)

    # For 'partial' — redirect to partial selection page
    if response == "partial":
        # Get team members for this project
        team_rows = db.execute(text("""
            SELECT a.employee_id, e.job_name, e.canonical_role, a.allocation_pct
            FROM allocations a
            JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
            WHERE a.project_id = :pid AND a.is_active_version = true
              AND a.resourcing_status = 'BILLABLE' AND a.end_date >= CURRENT_DATE
            ORDER BY e.job_name
        """), {"pid": row.project_id}).fetchall()

        return HTMLResponse(content=_partial_selection_page(
            token=token,
            project_id=row.project_id,
            client_id=row.client_id,
            end_date=row.project_end_date,
            team=[(r.employee_id, r.job_name, r.canonical_role, float(r.allocation_pct)) for r in team_rows],
        ))

    # Record response (no_extension or extend)
    db.execute(text("""
        UPDATE extension_confirmations
        SET response = :response, responded_at = NOW()
        WHERE token = :token
    """), {"response": response, "token": token})
    db.commit()

    if response == "no_extension":
        msg = f"✅ Confirmed: <strong>{row.client_id}</strong> will NOT be extended.<br>All {row.headcount} resources will become available for new projects."
    else:
        msg = f"✅ Confirmed: <strong>{row.client_id}</strong> will be extended.<br>All {row.headcount} resources are locked and will NOT be recommended elsewhere."

    return HTMLResponse(content=_response_page(msg, error=False))


class PartialResponseRequest(BaseModel):
    token: str
    staying_employee_ids: list[str] = []
    new_end_date: str | None = None
    notes: str | None = None


@router.post("/extension-response/partial")
def handle_partial_response(
    req: PartialResponseRequest,
    db: Session = Depends(get_db),
):
    """
    Handle partial extension response — EM selects which employees stay.
    Called from the partial selection page form.
    """
    from fastapi.responses import HTMLResponse

    row = db.execute(text("""
        SELECT id, project_id, client_id, headcount, response
        FROM extension_confirmations
        WHERE token = :token
    """), {"token": req.token}).fetchone()

    if not row:
        return HTMLResponse(content=_response_page("Invalid or expired link.", error=True), status_code=404)

    if row.response is not None:
        return HTMLResponse(content=_response_page(
            f"Already responded for {row.client_id}.", error=False
        ))

    # Record partial response
    db.execute(text("""
        UPDATE extension_confirmations
        SET response = 'partial',
            responded_at = NOW(),
            staying_employee_ids = :staying,
            new_end_date = :new_end,
            notes = :notes
        WHERE token = :token
    """), {
        "staying": req.staying_employee_ids if req.staying_employee_ids else None,
        "new_end": req.new_end_date,
        "notes": req.notes,
        "token": req.token,
    })
    db.commit()

    staying_count = len(req.staying_employee_ids)
    leaving_count = (row.headcount or 0) - staying_count

    msg = f"✅ Confirmed: <strong>{row.client_id}</strong> — Partial extension.<br>{staying_count} staying, {leaving_count} becoming available."

    return HTMLResponse(content=_response_page(msg, error=False))


@router.get("/extension-confirmations")
def get_extension_confirmations(db: Session = Depends(get_db)):
    """Get all extension confirmations for display in the UI."""
    from app.services.extension_check import get_all_confirmations
    return get_all_confirmations(db)


@router.post("/extension-check/run")
def trigger_extension_check(db: Session = Depends(get_db)):
    """Manually trigger the extension check (sends emails for projects ending in 7 days)."""
    from app.services.extension_check import check_and_send_all
    result = check_and_send_all(db)
    return result


# ── HTML page builders for email callbacks ────────────────────────────────────

def _response_page(message: str, error: bool = False) -> str:
    """Simple HTML response page shown when EM clicks email button."""
    color = "#dc2626" if error else "#19105B"
    icon = "❌" if error else "✅"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SapienSync — Extension Response</title>
<style>body{{font-family:Arial,sans-serif;margin:0;padding:40px;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f9fafb}}
.card{{max-width:500px;background:white;border-radius:16px;padding:40px;text-align:center;box-shadow:0 4px 24px rgba(0,0,0,0.08)}}
h1{{color:{color};font-size:20px;margin:0 0 16px}}
p{{color:#374151;font-size:14px;line-height:1.6;margin:0}}
.brand{{font-size:11px;color:#9ca3af;margin-top:24px}}</style></head>
<body><div class="card">
<h1>{icon} Extension Response</h1>
<p>{message}</p>
<p class="brand">SapienSync Engine · Jman Group</p>
</div></body></html>"""


def _partial_selection_page(token: str, project_id: str, client_id: str, end_date, team: list) -> str:
    """HTML page with checkboxes for EM to select which team members stay."""
    base_url = settings.webhook_base_url

    team_rows = ""
    for emp_id, name, role, pct in team:
        team_rows += f"""
        <label style="display:flex;align-items:center;gap:12px;padding:12px 16px;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:8px;cursor:pointer;transition:all 0.15s"
               onmouseover="this.style.borderColor='#19105B'" onmouseout="this.style.borderColor='#e5e7eb'">
            <input type="checkbox" name="staying" value="{emp_id}" style="width:18px;height:18px;accent-color:#19105B">
            <div style="flex:1">
                <span style="font-size:14px;font-weight:600;color:#19105B">{name}</span>
                <span style="font-size:12px;color:#6b7280;margin-left:8px">{role} · {int(pct)}%</span>
            </div>
        </label>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>SapienSync — Partial Extension</title>
<style>body{{font-family:Arial,sans-serif;margin:0;padding:40px;background:#f9fafb;display:flex;justify-content:center}}
.card{{max-width:600px;width:100%;background:white;border-radius:16px;padding:32px;box-shadow:0 4px 24px rgba(0,0,0,0.08)}}
h1{{color:#19105B;font-size:20px;margin:0 0 4px}}
.sub{{color:#6b7280;font-size:13px;margin:0 0 24px}}
.btn{{display:inline-block;padding:12px 32px;background:#19105B;color:#fff;font-size:14px;font-weight:600;border:none;border-radius:10px;cursor:pointer;margin-top:16px}}
.btn:hover{{background:#3411A3}}
label:has(input:checked){{border-color:#19105B!important;background:#19105B08}}
.field{{margin-top:16px}}
.field label{{display:block;font-size:12px;font-weight:600;color:#374151;margin-bottom:6px}}
.field input{{width:100%;padding:10px 14px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box}}
.brand{{font-size:11px;color:#9ca3af;margin-top:24px;text-align:center}}</style></head>
<body><div class="card">
<h1>Partial Extension — {client_id}</h1>
<p class="sub">Select which team members will STAY on the project (others will become available):</p>

<form id="partialForm">
    <input type="hidden" name="token" value="{token}">
    {team_rows}

    <div class="field">
        <label>New estimated end date (optional)</label>
        <input type="date" name="new_end_date" id="newEndDate">
    </div>
    <div class="field">
        <label>Notes (optional)</label>
        <input type="text" name="notes" id="notes" placeholder="e.g. Extension for 3 more months">
    </div>

    <button type="submit" class="btn">Confirm Partial Extension</button>
</form>

<p class="brand">SapienSync Engine · Jman Group</p>

<script>
document.getElementById('partialForm').addEventListener('submit', async function(e) {{
    e.preventDefault();
    const checked = Array.from(document.querySelectorAll('input[name="staying"]:checked')).map(cb => cb.value);
    const body = {{
        token: '{token}',
        staying_employee_ids: checked,
        new_end_date: document.getElementById('newEndDate').value || null,
        notes: document.getElementById('notes').value || null,
    }};
    const res = await fetch('{base_url}/api/rmg/extension-response/partial', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(body),
    }});
    const html = await res.text();
    document.body.innerHTML = html;
}});
</script>
</div></body></html>"""
