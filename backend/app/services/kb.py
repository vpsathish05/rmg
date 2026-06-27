"""Knowledge Base — build project embeddings and search similar past work as proof."""
from __future__ import annotations
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import AsyncOpenAI
from app.config import settings

_MODEL = "text-embedding-3-small"
_DIMS = 1536


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def _embed(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    resp = await client.embeddings.create(model=_MODEL, input=texts, dimensions=_DIMS)
    return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]


def _build_summary(row) -> str:
    """Build readable text summary for a project row (from the ETL query)."""
    lines = [
        f"Project {row.project_id} for {row.client_id}",
        f"COE: {row.proposition_coe or 'Unknown'}",
        f"Type: {row.type_of_project or 'Client Project'}",
        f"Status: {row.project_status or 'Unknown'}",
    ]
    if row.project_start_date and row.project_end_date:
        lines.append(f"Period: {row.project_start_date} to {row.project_end_date}")
    if row.team_roles:
        lines.append(f"Team: {row.team_roles}")
    if row.project_coes:
        lines.append(f"COEs: {row.project_coes}")
    if row.health_trend:
        lines.append(f"Health trend: {row.health_trend}")
    if row.total_hours:
        lines.append(f"Total hours logged: {float(row.total_hours):.0f}")
    if row.top_skills:
        lines.append(f"Skills: {row.top_skills}")
    return "\n".join(lines)


async def build_all(db: Session, batch_size: int = 50) -> int:
    """Embed all projects that have allocations. Returns count of upserted rows."""
    # Step 1: projects + team roles (lightweight — no huge tables)
    rows = db.execute(text("""
        SELECT
            p.project_id, p.client_id, p.proposition_coe, p.type_of_project,
            p.project_status, p.project_start_date, p.project_end_date,
            STRING_AGG(DISTINCT e.canonical_role || ' (' || a.resourcing_status || ')', ', ') AS team_roles,
            STRING_AGG(DISTINCT pc.coe, ', ') AS project_coes,
            NULL::text AS total_hours,
            NULL::text AS top_skills,
            NULL::text AS health_trend
        FROM projects p
        JOIN allocations a ON a.project_id = p.project_id AND a.is_active_version = true
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        LEFT JOIN project_coes pc ON pc.project_id = p.project_id
        WHERE p.is_active_version = true
        GROUP BY p.project_id, p.client_id, p.proposition_coe, p.type_of_project,
                 p.project_status, p.project_start_date, p.project_end_date
        LIMIT 500
    """)).fetchall()

    if not rows:
        return 0

    # Step 2: fetch WSR health per project (separate query — no cross join)
    proj_ids = [r.project_id for r in rows]
    health_rows = db.execute(text("""
        SELECT project_id,
               STRING_AGG(DISTINCT scope_status || '/' || schedule_status, ', ')
                   FILTER (WHERE scope_status IS NOT NULL) AS health_trend
        FROM weekly_status
        WHERE project_id = ANY(:ids)
        GROUP BY project_id
    """), {"ids": proj_ids}).fetchall()
    health_map = {r.project_id: r.health_trend for r in health_rows}

    # Merge health into rows as dicts
    import types
    enriched = []
    for r in rows:
        d = dict(r._mapping)
        d["health_trend"] = health_map.get(r.project_id)
        enriched.append(types.SimpleNamespace(**d))

    # Build summary texts
    summaries = [(r, _build_summary(r)) for r in enriched]

    # Embed in batches
    total = 0
    for i in range(0, len(summaries), batch_size):
        batch = summaries[i:i + batch_size]
        texts = [s for _, s in batch]
        embeddings = await _embed(texts)
        for (r, summary), emb in zip(batch, embeddings):
            # Upsert — delete existing then insert
            db.execute(text(
                "DELETE FROM project_embeddings WHERE project_id = :pid"
            ), {"pid": r.project_id})
            db.execute(text("""
                INSERT INTO project_embeddings (project_id, summary_text, embedding)
                VALUES (:pid, :txt, CAST(:emb AS vector))
            """), {"pid": r.project_id, "txt": summary, "emb": str(emb)})
            total += 1
        db.commit()

    return total


async def search_employee_proofs(
    db: Session,
    employee_id: str,
    query_text: str,
    limit: int = 2,
) -> list[dict]:
    """Return similar past projects this employee worked on — used as recommendation proof."""
    # Check if any embeddings exist
    count = db.execute(text("SELECT COUNT(*) FROM project_embeddings")).scalar()
    if not count:
        return []

    try:
        vec = (await _embed([query_text]))[0]
        vec_str = str(vec)
        rows = db.execute(text("""
            SELECT
                pe.project_id,
                pe.summary_text,
                p.client_id,
                p.proposition_coe,
                p.project_status,
                p.project_start_date,
                p.project_end_date,
                ROUND((1 - (pe.embedding <=> CAST(:vec AS vector)))::numeric, 3) AS similarity
            FROM project_embeddings pe
            JOIN projects p ON p.project_id = pe.project_id AND p.is_active_version = true
            JOIN allocations a ON a.project_id = pe.project_id AND a.is_active_version = true
            WHERE a.employee_id = :eid
            ORDER BY pe.embedding <=> CAST(:vec AS vector)
            LIMIT :lim
        """), {"vec": vec_str, "eid": employee_id, "lim": limit}).fetchall()

        return [
            {
                "project_id": r.project_id,
                "client_id": r.client_id,
                "coe": r.proposition_coe,
                "status": r.project_status,
                "start_date": str(r.project_start_date) if r.project_start_date else None,
                "end_date": str(r.project_end_date) if r.project_end_date else None,
                "similarity": float(r.similarity),
            }
            for r in rows
        ]
    except Exception:
        return []
