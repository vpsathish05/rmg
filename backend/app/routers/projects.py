from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectHealth

router = APIRouter()

_RAG_RANK = {"RED": 0, "AMBER": 1, "GREEN": 2, "NO_COLOR": 3}


def _overall(statuses):
    worst = min((_RAG_RANK.get(s, 3) for s in statuses if s), default=3)
    return {0: "RED", 1: "AMBER", 2: "GREEN", 3: "NO_COLOR"}[worst]


@router.get("/health", response_model=List[ProjectHealth])
def project_health(
    health: str = Query(None),  # RED / AMBER / GREEN / NO_COLOR
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT
            p.project_id,
            p.client_id,
            p.project_status,
            p.proposition_coe,
            p.project_start_date,
            p.project_end_date,
            ws.scope_status,
            ws.schedule_status,
            ws.quality_status,
            ws.csat_status,
            ws.team_status,
            ws.week_end
        FROM projects p
        LEFT JOIN LATERAL (
            SELECT scope_status, schedule_status, quality_status,
                   csat_status, team_status, week_end
            FROM weekly_status
            WHERE project_id = p.project_id
            ORDER BY week_end DESC NULLS LAST
            LIMIT 1
        ) ws ON true
        WHERE p.project_status IN ('ACTIVE','DEAL WON')
          AND p.is_active_version = true
        ORDER BY p.client_id, p.project_id
    """)).fetchall()

    result = []
    for r in rows:
        oh = _overall([r.scope_status, r.schedule_status,
                       r.quality_status, r.csat_status, r.team_status])
        if health and oh != health.upper():
            continue
        result.append(ProjectHealth(
            project_id=r.project_id,
            client_id=r.client_id,
            project_status=r.project_status,
            proposition_coe=r.proposition_coe,
            project_start_date=r.project_start_date,
            project_end_date=r.project_end_date,
            scope_status=r.scope_status,
            schedule_status=r.schedule_status,
            quality_status=r.quality_status,
            csat_status=r.csat_status,
            team_status=r.team_status,
            overall_health=oh,
            week_end=r.week_end,
        ))
    return result


@router.get("/overrunning")
def overrunning_projects(db: Session = Depends(get_db)):
    """Projects where project_end_date < today and status is still ACTIVE."""
    rows = db.execute(text("""
        SELECT
            p.project_id,
            p.client_id,
            p.project_status,
            p.proposition_coe,
            p.project_end_date,
            (CURRENT_DATE - p.project_end_date) AS days_overrun,
            COUNT(DISTINCT a.employee_id) AS headcount
        FROM projects p
        LEFT JOIN allocations a
            ON a.project_id = p.project_id
            AND a.is_active = true AND a.is_active_version = true
        WHERE p.project_status = 'ACTIVE'
          AND p.is_active_version = true
          AND p.project_end_date IS NOT NULL
          AND p.project_end_date < CURRENT_DATE
        GROUP BY p.project_id, p.client_id, p.project_status, p.proposition_coe, p.project_end_date
        ORDER BY days_overrun DESC
        LIMIT 50
    """)).fetchall()
    return [
        {
            "project_id": r.project_id,
            "client_id": r.client_id,
            "project_status": r.project_status,
            "proposition_coe": r.proposition_coe,
            "project_end_date": r.project_end_date.isoformat() if r.project_end_date else None,
            "days_overrun": int(r.days_overrun),
            "headcount": int(r.headcount),
        }
        for r in rows
    ]


@router.get("/ramp-down")
def ramp_down_projects(
    days: int = Query(60, description="Projects ending within this many days"),
    db: Session = Depends(get_db),
):
    """Projects ending within N days — candidates for ramp-down planning."""
    rows = db.execute(text("""
        SELECT
            p.project_id,
            p.client_id,
            p.project_status,
            p.proposition_coe,
            p.project_end_date,
            (p.project_end_date - CURRENT_DATE) AS days_remaining,
            COUNT(DISTINCT a.employee_id) AS headcount
        FROM projects p
        LEFT JOIN allocations a
            ON a.project_id = p.project_id
            AND a.is_active = true AND a.is_active_version = true
        WHERE p.project_status IN ('ACTIVE', 'DEAL WON')
          AND p.is_active_version = true
          AND p.project_end_date IS NOT NULL
          AND p.project_end_date >= CURRENT_DATE
          AND p.project_end_date <= CURRENT_DATE + :days_interval
        GROUP BY p.project_id, p.client_id, p.project_status, p.proposition_coe, p.project_end_date
        ORDER BY days_remaining ASC
        LIMIT 50
    """), {"days_interval": f"{days} days"}).fetchall()
    return [
        {
            "project_id": r.project_id,
            "client_id": r.client_id,
            "project_status": r.project_status,
            "proposition_coe": r.proposition_coe,
            "project_end_date": r.project_end_date.isoformat() if r.project_end_date else None,
            "days_remaining": int(r.days_remaining),
            "headcount": int(r.headcount),
        }
        for r in rows
    ]


@router.get("")
def list_projects(
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    from sqlalchemy import select
    q = (
        __import__("sqlalchemy", fromlist=["select"]).select(Project)
        .where(Project.is_active_version == True)
    )
    if status:
        q = q.where(Project.project_status == status.upper())
    return db.execute(q).scalars().all()


@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj
