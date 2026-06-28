from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()


@router.get("/network")
def network(db: Session = Depends(get_db)):
    """Projects as nodes, shared employees as links between projects."""
    # Get projects with team info
    proj_rows = db.execute(text("""
        SELECT p.project_id, p.client_id, p.proposition_coe, p.project_start_date, p.project_end_date,
               COUNT(DISTINCT a.employee_id) AS team_size
        FROM projects p
        JOIN allocations a ON a.project_id = p.project_id AND a.is_active_version = true AND a.is_active = true
        WHERE p.is_active_version = true AND UPPER(p.project_status) = 'ACTIVE'
          AND p.client_id != 'CLIENT_127'
        GROUP BY p.project_id, p.client_id, p.proposition_coe, p.project_start_date, p.project_end_date
        HAVING COUNT(DISTINCT a.employee_id) >= 3
        ORDER BY COUNT(DISTINCT a.employee_id) DESC
        LIMIT 60
    """)).fetchall()

    nodes = [{
        "id": r.project_id,
        "client": r.client_id,
        "coe": r.proposition_coe,
        "team_size": int(r.team_size),
        "start": r.project_start_date.isoformat() if r.project_start_date else None,
        "end": r.project_end_date.isoformat() if r.project_end_date else None,
    } for r in proj_rows]

    proj_ids = [r.project_id for r in proj_rows]
    if not proj_ids:
        return {"nodes": [], "links": []}

    # Find shared employees between projects (links)
    link_rows = db.execute(text("""
        SELECT a1.project_id AS source, a2.project_id AS target,
               COUNT(DISTINCT a1.employee_id) AS shared
        FROM allocations a1
        JOIN allocations a2 ON a1.employee_id = a2.employee_id
          AND a2.is_active = true AND a2.is_active_version = true
          AND a1.project_id < a2.project_id
        WHERE a1.is_active = true AND a1.is_active_version = true
          AND a1.project_id = ANY(:ids) AND a2.project_id = ANY(:ids)
        GROUP BY a1.project_id, a2.project_id
        HAVING COUNT(DISTINCT a1.employee_id) >= 2
        ORDER BY shared DESC
        LIMIT 150
    """), {"ids": proj_ids}).fetchall()

    links = [{"source": r.source, "target": r.target, "shared": int(r.shared)} for r in link_rows]

    return {"nodes": nodes, "links": links}


@router.get("/timeline/{project_id}")
def timeline(project_id: str, db: Session = Depends(get_db)):
    """Resource lifecycle for a specific project."""
    proj = db.execute(text("""
        SELECT project_id, client_id, proposition_coe, project_start_date, project_end_date, project_status
        FROM projects WHERE project_id = :pid AND is_active_version = true
    """), {"pid": project_id}).fetchone()
    if not proj:
        return {"project": None, "resources": []}

    rows = db.execute(text("""
        SELECT a.employee_id, e.job_name, e.canonical_role, a.start_date, a.end_date,
               a.allocation_pct, a.resourcing_status
        FROM allocations a
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        WHERE a.project_id = :pid AND a.is_active_version = true AND a.is_active = true
        ORDER BY a.start_date, e.canonical_role
    """), {"pid": project_id}).fetchall()

    return {
        "project": {
            "id": proj.project_id,
            "client": proj.client_id,
            "coe": proj.proposition_coe,
            "start": proj.project_start_date.isoformat() if proj.project_start_date else None,
            "end": proj.project_end_date.isoformat() if proj.project_end_date else None,
            "status": proj.project_status,
        },
        "resources": [{
            "employee_id": r.employee_id,
            "job_name": r.job_name,
            "canonical_role": r.canonical_role,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "allocation_pct": float(r.allocation_pct) if r.allocation_pct else None,
            "status": r.resourcing_status,
        } for r in rows],
    }



@router.get("/employee/{employee_id}")
def employee_timeline(employee_id: str, db: Session = Depends(get_db)):
    """12-month view of an employee's project allocations (6 months back + 6 months forward)."""
    emp = db.execute(text("""
        SELECT employee_id, job_name, canonical_role, department_name, location
        FROM employees WHERE employee_id = :eid AND is_active_version = true
    """), {"eid": employee_id}).fetchone()
    if not emp:
        return {"employee": None, "allocations": []}

    rows = db.execute(text("""
        SELECT a.project_id, p.client_id, p.proposition_coe, a.start_date, a.end_date,
               a.allocation_pct, a.resourcing_status, p.project_status
        FROM allocations a
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        WHERE a.employee_id = :eid AND a.is_active_version = true
          AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE - INTERVAL '6 months')
          AND a.start_date <= CURRENT_DATE + INTERVAL '6 months'
        ORDER BY a.start_date
    """), {"eid": employee_id}).fetchall()

    return {
        "employee": {
            "id": emp.employee_id,
            "job_name": emp.job_name,
            "canonical_role": emp.canonical_role,
            "department": emp.department_name,
            "location": emp.location,
        },
        "allocations": [{
            "project_id": r.project_id,
            "client": r.client_id,
            "coe": r.proposition_coe,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "allocation_pct": float(r.allocation_pct) if r.allocation_pct else None,
            "status": r.resourcing_status,
            "project_status": r.project_status,
        } for r in rows],
    }


@router.get("/employees/search")
def search_employees(q: str = "", db: Session = Depends(get_db)):
    """Search employees by ID or name."""
    rows = db.execute(text("""
        SELECT employee_id, job_name, canonical_role
        FROM employees
        WHERE is_active_version = true AND account_status = true
          AND (employee_id ILIKE :q OR job_name ILIKE :q)
        ORDER BY employee_id
        LIMIT 20
    """), {"q": f"%{q}%"}).fetchall()
    return [{"id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role} for r in rows]
