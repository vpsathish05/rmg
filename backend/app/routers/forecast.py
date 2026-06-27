from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.database import get_db
from app.models.pipeline import PipelineRequest

router = APIRouter()


@router.get("")
def list_pipeline(db: Session = Depends(get_db)):
    rows = db.execute(select(PipelineRequest)).scalars().all()
    return rows


@router.get("/outlook")
def pipeline_outlook(db: Session = Depends(get_db)):
    """6-month demand outlook: requests grouped by month × role with weighted FTE."""
    rows = db.execute(text("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', likely_start_date), 'YYYY-MM') AS month,
            COALESCE(role_code_raw, 'Unknown')                           AS role,
            COUNT(*)                                                      AS request_count,
            ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0)::numeric, 2) AS total_fte,
            ROUND(SUM(
                COALESCE(allocation_pct, 100) / 100.0
                * COALESCE(probability_weight, 0.5)
            )::numeric, 2)                                               AS weighted_fte
        FROM pipeline_requests
        WHERE likely_start_date IS NOT NULL
          AND likely_start_date >= CURRENT_DATE
          AND likely_start_date <= CURRENT_DATE + INTERVAL '6 months'
        GROUP BY DATE_TRUNC('month', likely_start_date), COALESCE(role_code_raw, 'Unknown')
        ORDER BY month, total_fte DESC
    """)).fetchall()

    # Reshape into { month: string, roles: { role: {count, fte, weighted_fte} }[] }
    months: dict = {}
    for r in rows:
        m = r.month
        if m not in months:
            months[m] = {"month": m, "total_fte": 0.0, "weighted_fte": 0.0, "roles": []}
        months[m]["roles"].append({
            "role": r.role,
            "request_count": int(r.request_count),
            "total_fte": float(r.total_fte),
            "weighted_fte": float(r.weighted_fte),
        })
        months[m]["total_fte"] = round(months[m]["total_fte"] + float(r.total_fte), 2)
        months[m]["weighted_fte"] = round(months[m]["weighted_fte"] + float(r.weighted_fte), 2)

    return list(months.values())
