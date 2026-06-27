"""
Pre-compute and cache role recommendations.

Runs nightly at 2am IST via APScheduler, or manually via:
    PYTHONPATH=. python -m etl.compute_recommendations

Stores results in role_recommendations table so the UI loads instantly.
"""
from __future__ import annotations
import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services import scorer as scoring_svc
from app.services.llm import generate_rationales_batch
from app.services.kb import search_employee_proofs
from app.schemas.recommend import RecommendRequest

log = logging.getLogger(__name__)

# Prevent concurrent runs
_running = False


def is_running() -> bool:
    return _running


def _auto_coe(db: Session, canonical_roles: list[str]) -> str | None:
    """Find the most common assessed COE for the given canonical roles."""
    if not canonical_roles:
        return None
    row = db.execute(text("""
        SELECT INITCAP(TRIM(es.coe)) AS coe, COUNT(*) AS cnt
        FROM employee_skills es
        JOIN employees e
          ON e.employee_id = es.employee_id
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
    return row.coe if row else None


def _fmt_candidate(c, kb_proofs: dict) -> dict:
    return {
        "employee_id":           c.employee_id,
        "job_name":              c.job_name,
        "canonical_role":        c.canonical_role,
        "location":              c.location,
        "department_name":       c.department_name,
        "current_allocated_pct": c.current_allocated_pct,
        "available_pct":         c.available_pct,
        "category":              c.category,
        "total_score":           c.total_score,
        "skill_score":           c.skill_score,
        "comp_score":            c.comp_score,
        "avail_score":           c.avail_score,
        "prod_score":            c.prod_score,
        "has_competency":        c.has_competency,
        "rationale":             c.rationale,
        "kb_proof":              kb_proofs.get(c.employee_id, []),
    }


def _upsert_error(db: Session, role_id: int, reason: str) -> None:
    db.execute(text("""
        INSERT INTO role_recommendations
            (pipeline_role_id, status, computed_at)
        VALUES (:rid, 'error', NOW())
        ON CONFLICT (pipeline_role_id) DO UPDATE
            SET status = 'error', computed_at = NOW()
    """), {"rid": role_id})
    db.commit()
    log.warning("role %s → error: %s", role_id, reason)


async def compute_all(db: Session) -> dict:
    """
    Score every Not Resourced pipeline role with rationale + KB proofs.
    Upserts results into role_recommendations.
    Returns a summary dict.
    """
    global _running
    if _running:
        return {"status": "already_running"}

    _running = True
    started_at = datetime.now(timezone.utc)
    done = errors = skipped = 0

    try:
        roles = db.execute(text("""
            SELECT id, role_code_raw, canonical_roles,
                   allocation_pct, duration_weeks, required_skills
            FROM pipeline_requests
            WHERE LOWER(status) = 'not resourced'
            ORDER BY id
        """)).fetchall()

        log.info("rec_cache: computing %d Not Resourced roles…", len(roles))

        for role in roles:
            try:
                canonical = role.canonical_roles or []
                coe = _auto_coe(db, canonical)

                if not coe:
                    _upsert_error(db, role.id, "no COE detected")
                    errors += 1
                    continue

                # Score all candidates
                scored = scoring_svc.score_all(
                    db=db,
                    canonical_roles=canonical,
                    always_best_match=False,
                    coe=coe,
                    requested_alloc_pct=float(role.allocation_pct or 100),
                )

                if not scored:
                    skipped += 1
                    _upsert_error(db, role.id, "scorer returned 0 candidates")
                    continue

                # GPT rationale for top 10 (concurrent per role)
                fake_req = RecommendRequest(
                    role_code=role.role_code_raw or "Unknown",
                    coe=coe,
                    allocation_pct=float(role.allocation_pct or 100),
                    duration_weeks=role.duration_weeks,
                    skills_required=role.required_skills,
                )
                scored = await generate_rationales_batch(scored, fake_req, top_n=10)

                # KB proofs for top 6 (Available + BestMatch)
                query_text = (
                    f"{role.role_code_raw or ''} {coe} {role.required_skills or ''}"
                ).strip()
                top6 = [c for c in scored if c.category in ("Available", "BestMatch")][:6]
                proof_results = await asyncio.gather(
                    *[search_employee_proofs(db, c.employee_id, query_text) for c in top6],
                    return_exceptions=True,
                )
                kb_proofs: dict[str, list] = {}
                kb_active = False
                for c, proofs in zip(top6, proof_results):
                    if isinstance(proofs, list) and proofs:
                        kb_proofs[c.employee_id] = proofs
                        kb_active = True

                # Split categories (top 3 each)
                available  = [c for c in scored if c.category == "Available"][:3]
                best_match = [c for c in scored if c.category == "BestMatch"][:3]
                no_resource = len(available) + len(best_match) == 0

                hire_signal = None
                if no_resource:
                    hire_signal = (
                        f"No internal candidate available for '{role.role_code_raw}' in {coe}. "
                        f"{len(scored)} evaluated — all at capacity or lack {coe} skills. "
                        f"Consider external hire or adjacent COE redeployment."
                    )

                # Upsert
                db.execute(text("""
                    INSERT INTO role_recommendations
                        (pipeline_role_id, coe, available, best_match, no_resource,
                         hire_signal, kb_active, total_evaluated, computed_at, status)
                    VALUES
                        (:rid, :coe,
                         CAST(:available AS jsonb), CAST(:best_match AS jsonb),
                         :no_resource, :hire_signal, :kb_active,
                         :total_evaluated, NOW(), 'done')
                    ON CONFLICT (pipeline_role_id) DO UPDATE SET
                        coe            = EXCLUDED.coe,
                        available      = EXCLUDED.available,
                        best_match     = EXCLUDED.best_match,
                        no_resource    = EXCLUDED.no_resource,
                        hire_signal    = EXCLUDED.hire_signal,
                        kb_active      = EXCLUDED.kb_active,
                        total_evaluated = EXCLUDED.total_evaluated,
                        computed_at    = NOW(),
                        status         = 'done'
                """), {
                    "rid":            role.id,
                    "coe":            coe,
                    "available":      json.dumps([_fmt_candidate(c, kb_proofs) for c in available]),
                    "best_match":     json.dumps([_fmt_candidate(c, kb_proofs) for c in best_match]),
                    "no_resource":    no_resource,
                    "hire_signal":    hire_signal,
                    "kb_active":      kb_active,
                    "total_evaluated": len(scored),
                })
                db.commit()
                done += 1
                log.info("  ✓ role %s (%s) — %d avail, %d best_match",
                         role.id, role.role_code_raw, len(available), len(best_match))

            except Exception as exc:
                db.rollback()
                errors += 1
                log.error("  ✗ role %s failed: %s", role.id, exc)

        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        summary = {
            "status":  "done",
            "total":   len(roles),
            "done":    done,
            "errors":  errors,
            "skipped": skipped,
            "elapsed_seconds": round(elapsed, 1),
        }
        log.info("rec_cache: finished — %s", summary)
        return summary

    finally:
        _running = False
