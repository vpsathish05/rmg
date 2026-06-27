from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models.allocation import Allocation

router = APIRouter()


@router.get("")
def list_allocations(
    employee_id: str = Query(None),
    project_id: str = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = select(Allocation).where(Allocation.is_active_version == True)
    if active_only:
        q = q.where(Allocation.is_active == True)
    if employee_id:
        q = q.where(Allocation.employee_id == employee_id)
    if project_id:
        q = q.where(Allocation.project_id == project_id)
    return db.execute(q).scalars().all()
