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
- Required allocation: {req.allocation_pct or 100:.0f}%
{f"- Duration: {req.duration_weeks} weeks" if req.duration_weeks else ""}
{skills_line}
Candidate:
- ID: {candidate.employee_id}
- Title: {candidate.job_name or 'Unknown'}
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



async def rerank_candidates(
    candidates: list[CandidateScore],
    req: RecommendRequest,
    top_n: int = 10,
) -> list[CandidateScore]:
    """Use GPT-4o to re-rank the top N candidates based on holistic fit."""
    top = candidates[:top_n]
    if len(top) < 2:
        return candidates

    def _fmt_line(i: int, c: CandidateScore) -> str:
        sem = f"{c.semantic_score:.0%}" if c.semantic_score is not None else "N/A"
        return (
            f"{i+1}. {c.employee_id} | {c.canonical_role or 'Unknown'} | {c.location or 'Unknown'} | "
            f"skill={c.skill_score:.0%} avail={c.available_pct:.0f}% "
            f"semantic={sem} total={c.total_score:.0%} | cat={c.category}"
        )

    candidate_lines = "\n".join(_fmt_line(i, c) for i, c in enumerate(top))

    prompt = f"""You are the RMG (Resource Management Group) AI at JMan Group.

Re-rank these {len(top)} candidates for best fit to this role. Consider:
- Skill alignment with required skills (most important)
- Availability (prefer candidates with capacity)
- Location fit
- Role seniority match
- Overall balance of scores

Role request:
- Role: {req.role_code}
- COE: {req.coe}
- Required allocation: {req.allocation_pct or 100:.0f}%
- Duration: {req.duration_weeks or 'Unknown'} weeks
- Required skills: {req.skills_required or 'Not specified'}

Candidates (current ranking):
{candidate_lines}

Reply with ONLY the re-ranked employee IDs in order, one per line. Best fit first. No explanations."""

    try:
        resp = await get_client().chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.2,
        )
        answer = resp.choices[0].message.content.strip()

        # Parse IDs from response
        reranked_ids = [line.strip().split("|")[0].strip().split(".")[-1].strip()
                        for line in answer.split("\n") if line.strip()]
        # Clean: extract just EMP IDs
        reranked_ids = [id for id in reranked_ids if id.startswith("EMP")]

        if len(reranked_ids) < 2:
            return candidates

        # Reorder top candidates based on LLM ranking
        id_to_candidate = {c.employee_id: c for c in top}
        reranked = []
        for eid in reranked_ids:
            if eid in id_to_candidate:
                reranked.append(id_to_candidate.pop(eid))
        # Append any not mentioned by LLM
        reranked.extend(id_to_candidate.values())
        # Append the rest beyond top_n
        return reranked + candidates[top_n:]

    except Exception:
        return candidates


async def generate_smart_hire_signal(
    req: RecommendRequest,
    total_evaluated: int,
    top_stretch: list[CandidateScore] | None = None,
) -> str:
    """Generate an actionable hiring recommendation when no internal match exists."""
    stretch_info = ""
    if top_stretch:
        stretch_info = "\nClosest internal candidates (all Stretch/weak fit):\n" + "\n".join(
            f"- {c.employee_id}: {c.canonical_role}, skill={c.skill_score:.0%}, avail={c.available_pct:.0f}%"
            for c in top_stretch[:3]
        )

    prompt = f"""You are the RMG AI at JMan Group consulting firm.

No internal candidate is available for this role. Generate a concise, actionable hire recommendation (3-4 sentences).

Include: specific profile to hire (seniority, skills, experience years), engagement type (FTE vs contract), and any adjacent internal redeployment options.

Role details:
- Role: {req.role_code}
- COE: {req.coe}
- Allocation: {req.allocation_pct or 100:.0f}%
- Duration: {req.duration_weeks or 'Unknown'} weeks
- Required skills: {req.skills_required or 'Not specified'}
- Total evaluated: {total_evaluated} employees
{stretch_info}

Reply with ONLY the hire recommendation. Be specific and actionable."""

    try:
        resp = await get_client().chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return (
            f"No internal candidate available for '{req.role_code}' in {req.coe}. "
            f"{total_evaluated} evaluated — all at capacity or lack required skills. "
            f"Consider external hire or adjacent COE redeployment."
        )
