from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.database import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeAvailability, EmployeeAllocationDetail

router = APIRouter()


def _alloc_status(pct: float) -> str:
    if pct == 0:
        return "On Bench"
    if pct < 50:
        return "Available"
    if pct < 100:
        return "Partial"
    if pct == 100:
        return "Allocated"
    return "Over-allocated"


# Priority order for billability: SHADOW > UNBILLED > BILLABLE
_BILL_RANK = {"SHADOW": 0, "UNBILLED": 1, "BILLABLE": 2}


def _worst_billability(shadow: int, unbilled: int, billable: int) -> str | None:
    if shadow > 0:
        return "SHADOW"
    if unbilled > 0:
        return "UNBILLED"
    if billable > 0:
        return "BILLABLE"
    return None


@router.get("", response_model=List[EmployeeAvailability])
def list_employees(
    department: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT
            e.employee_id,
            e.job_name,
            e.canonical_role,
            e.department_name,
            e.location,
            COALESCE(SUM(a.allocation_pct), 0) AS allocated_pct,
            COUNT(CASE WHEN UPPER(a.resourcing_status) = 'SHADOW'   THEN 1 END) AS shadow_count,
            COUNT(CASE WHEN UPPER(a.resourcing_status) = 'UNBILLED'  THEN 1 END) AS unbilled_count,
            COUNT(CASE WHEN UPPER(a.resourcing_status) = 'BILLABLE'  THEN 1 END) AS billable_count,
            MIN(CASE WHEN a.end_date IS NOT NULL AND (a.is_open_ended = false OR a.is_open_ended IS NULL)
                     THEN a.end_date END) AS nearest_end_date
        FROM employees e
        LEFT JOIN allocations a
            ON a.employee_id = e.employee_id
            AND a.is_active = true
            AND a.is_active_version = true
        LEFT JOIN projects p
            ON p.project_id = a.project_id AND p.is_active_version = true
            AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        WHERE e.account_status = true
          AND e.is_active_version = true
          AND e.date_of_resignation IS NULL
          AND e.job_name IS NOT NULL
        GROUP BY e.employee_id, e.job_name, e.canonical_role, e.department_name, e.location
        ORDER BY allocated_pct ASC
    """)).fetchall()

    result = []
    for r in rows:
        allocated = float(r.allocated_pct or 0)
        available = max(0.0, 100.0 - allocated)
        st = _alloc_status(allocated)
        if department and (r.department_name or "").lower() != department.lower():
            continue
        if status and st != status:
            continue
        result.append(EmployeeAvailability(
            employee_id=r.employee_id,
            job_name=r.job_name,
            canonical_role=r.canonical_role,
            department_name=r.department_name,
            location=r.location,
            allocated_pct=allocated,
            available_pct=available,
            allocation_status=st,
            billability=_worst_billability(
                int(r.shadow_count or 0),
                int(r.unbilled_count or 0),
                int(r.billable_count or 0),
            ),
            nearest_end_date=r.nearest_end_date,
        ))
    return result


@router.get("/{employee_id}/allocations", response_model=List[EmployeeAllocationDetail])
def employee_allocations(employee_id: str, db: Session = Depends(get_db)):
    """Return all active allocations for an employee with project & billability details."""
    rows = db.execute(text("""
        SELECT
            a.project_id,
            p.client_id,
            a.allocation_pct,
            a.resourcing_status,
            a.start_date,
            a.end_date,
            COALESCE(a.is_open_ended, false) AS is_open_ended,
            CASE
                WHEN a.end_date IS NOT NULL AND (a.is_open_ended = false OR a.is_open_ended IS NULL)
                THEN (a.end_date - CURRENT_DATE)
                ELSE NULL
            END AS days_remaining
        FROM allocations a
        LEFT JOIN projects p
            ON p.project_id = a.project_id
            AND p.is_active_version = true
        WHERE a.employee_id = :eid
          AND a.is_active = true
          AND a.is_active_version = true
        ORDER BY a.end_date ASC NULLS LAST, a.project_id
    """), {"eid": employee_id}).fetchall()

    return [
        EmployeeAllocationDetail(
            project_id=r.project_id,
            client_id=r.client_id,
            allocation_pct=float(r.allocation_pct) if r.allocation_pct else None,
            resourcing_status=r.resourcing_status,
            start_date=r.start_date,
            end_date=r.end_date,
            is_open_ended=bool(r.is_open_ended),
            days_remaining=int(r.days_remaining) if r.days_remaining is not None else None,
        )
        for r in rows
    ]


@router.get("/{employee_id}")
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp
