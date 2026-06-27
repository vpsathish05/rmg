"""OpenAI integration — generates recommendation rationale per candidate."""
from __future__ import annotations
import asyncio
from openai import AsyncOpenAI
from app.config import settings
from app.services.scorer import CandidateScore
from app.schemas.recommend import RecommendRequest

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_rationale(candidate: CandidateScore, req: RecommendRequest) -> str:
    """Return a 2-3 sentence rationale for why this candidate fits (or doesn't)."""
    roles_str = ", ".join(req.role_code.split("/")) if "/" in req.role_code else req.role_code
    comp_line = (
        f"- Competency score: {candidate.comp_score:.0%}\n"
        if candidate.comp_score is not None
        else ""
    )
    skills_line = (
        f"- Skills required: {req.skills_required}\n"
        if req.skills_required
        else ""
    )
    prompt = f"""You are the Resource Management Group (RMG) assistant at JMan Group, a consulting firm.

Evaluate this candidate for a resource request. Write 2-3 concise, factual sentences.
Focus on: skill fit for the requested technology, availability, and any capacity concerns.
Do not use bullet points or headers. Be direct and specific.

Resource request:
- Role: {req.role_code} ({roles_str})
- Technology / COE: {req.coe}
- Required allocation: {req.allocation_pct:.0f}%
{f"- Duration: {req.duration_weeks} weeks" if req.duration_weeks else ""}
{skills_line}
Candidate:
- ID: {candidate.employee_id}
- Title: {candidate.job_name}
- Location: {candidate.location or "Not specified"}
- Current allocation: {candidate.current_allocated_pct:.0f}% (available: {candidate.available_pct:.0f}%)
- Skill score in {req.coe}: {candidate.skill_score:.0%}
{comp_line}- Overall match score: {candidate.total_score:.0%}
- Recommendation category: {candidate.category}
"""
    resp = await get_client().chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()


async def generate_rationales_batch(
    candidates: list[CandidateScore],
    req: RecommendRequest,
    top_n: int = 10,
) -> list[CandidateScore]:
    """Add rationale to the top N candidates in parallel."""
    top = candidates[:top_n]
    try:
        rationales = await asyncio.gather(
            *[generate_rationale(c, req) for c in top],
            return_exceptions=True,
        )
        for c, r in zip(top, rationales):
            c.rationale = r if isinstance(r, str) else None
    except Exception:
        pass  # rationales are optional — don't fail the whole request
    return candidates
