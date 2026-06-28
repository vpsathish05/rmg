"""
Build employee skill embeddings — concatenates all assessed skills per employee
into a text profile, then embeds with text-embedding-3-small.

Run: PYTHONPATH=. python -m etl.build_skill_embeddings
"""
import asyncio
import logging
from sqlalchemy import text
from app.database import SessionLocal
from app.services.kb import _embed

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BATCH_SIZE = 50


async def build_all():
    db = SessionLocal()
    try:
        # Get all employees with assessed skills (score > 0)
        rows = db.execute(text("""
            SELECT e.employee_id,
                   e.job_name,
                   e.canonical_role,
                   STRING_AGG(DISTINCT es.coe, ', ') AS coes,
                   STRING_AGG(
                       DISTINCT es.coe_skill || ' (' || es.skill_category || ': ' || es.sub_skill || ', score=' || es.score || ')',
                       '; '
                   ) AS skills_detail
            FROM employees e
            JOIN employee_skills es ON es.employee_id = e.employee_id
                AND es.is_assessed = true AND es.score IS NOT NULL AND es.score > 0
            WHERE e.account_status = true AND e.is_active_version = true
            GROUP BY e.employee_id, e.job_name, e.canonical_role
        """)).fetchall()

        log.info(f"Building embeddings for {len(rows)} employees with skills...")

        total = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            texts = []
            for r in batch:
                profile = f"Role: {r.canonical_role or r.job_name or 'Unknown'}. COEs: {r.coes or 'None'}. Skills: {r.skills_detail}"
                texts.append(profile[:8000])  # truncate to embedding limit

            embeddings = await _embed(texts)

            for r, emb, txt in zip(batch, embeddings, texts):
                db.execute(text("""
                    INSERT INTO employee_skill_embeddings (employee_id, skill_text, embedding, updated_at)
                    VALUES (:eid, :txt, CAST(:emb AS vector), NOW())
                    ON CONFLICT (employee_id) DO UPDATE SET
                        skill_text = EXCLUDED.skill_text,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """), {"eid": r.employee_id, "txt": txt, "emb": str(emb)})

            db.commit()
            total += len(batch)
            log.info(f"  Embedded {total}/{len(rows)} employees...")

        log.info(f"Done! {total} employee skill embeddings created.")
        return total
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(build_all())
