"""
Auto-reply with AI recommendations when an EXTEND email request is processed.

Flow:
  1. Extract role, COE, skills from parsed_json
  2. Auto-detect COE (SQL → global → LLM fallback)
  3. Compute semantic scores (ANN)
  4. Run scorer
  5. Generate rationale for top 3
  6. Build professional reply HTML
  7. Send via ACS to source_email
  8. Update email_requests.status = 'REPLIED'
"""
from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

log = logging.getLogger(__name__)


async def auto_reply_recommendation(
    db: Session,
    email_request_id: str,
    parsed: dict,
    source_email: str,
) -> bool:
    """Run AI recommendation and send reply email. Returns True if sent."""
    from app.config import settings

    if not settings.acs_connection_string:
        log.warning("Auto-reply skipped: ACS not configured")
        return False

    # Extract role info from parsed email
    role = parsed.get("role") or parsed.get("canonical_role") or parsed.get("role_code")
    if not role:
        log.info("Auto-reply skipped for %s: no role in parsed data", email_request_id)
        return False

    coe = parsed.get("coe")
    skills = parsed.get("required_skills") or parsed.get("skills")
    client_name = parsed.get("client_name") or parsed.get("client") or "Unknown Client"
    project_id = parsed.get("project_id") or parsed.get("project_code") or ""
    allocation_pct = float(parsed.get("allocation_pct") or parsed.get("current_allocation_pct") or 100)
    duration_weeks = parsed.get("duration_weeks")
    employee_name = parsed.get("employee_name") or parsed.get("alloc_1_email") or ""

    # Auto-detect COE if not provided
    if not coe:
        from app.services.rec_cache import _auto_coe
        coe = await _auto_coe(db, [role], role, skills)

    if not coe:
        log.info("Auto-reply skipped for %s: could not detect COE", email_request_id)
        return False

    # Compute semantic scores via ANN
    from app.services.kb import compute_semantic_skill_scores_ann
    role_query = f"{role} {coe} {skills or ''}".strip()
    semantic_scores = await compute_semantic_skill_scores_ann(db, role_query, top_k=50) if role_query else None

    # Run scorer
    from app.services.scorer import score_all
    scored = score_all(
        db=db,
        canonical_roles=[role],
        always_best_match=False,
        coe=coe,
        requested_alloc_pct=allocation_pct,
        semantic_scores=semantic_scores,
    )

    if not scored:
        # No candidates — send hire signal reply
        hire_html = _build_no_resource_html(client_name, role, coe, employee_name, project_id)
        await _send_reply(settings, source_email, client_name, hire_html)
        _mark_replied(db, email_request_id)
        return True

    # Get top 3 Available + top 3 BestMatch
    available = [c for c in scored if c.category == "Available"][:3]
    best_match = [c for c in scored if c.category == "BestMatch"][:3]
    top_candidates = available + best_match

    if not top_candidates:
        # Only Stretch candidates — send hire signal
        hire_html = _build_no_resource_html(client_name, role, coe, employee_name, project_id)
        await _send_reply(settings, source_email, client_name, hire_html)
        _mark_replied(db, email_request_id)
        return True

    # Generate rationale for top candidate only (keep it fast)
    rationale = None
    try:
        from app.services.llm import generate_rationale
        from app.schemas.recommend import RecommendRequest
        fake_req = RecommendRequest(
            role_code=role, coe=coe, allocation_pct=allocation_pct,
            duration_weeks=int(duration_weeks) if duration_weeks else None,
            skills_required=skills,
        )
        rationale = await generate_rationale(top_candidates[0], fake_req)
    except Exception as e:
        log.warning("Rationale generation failed: %s", e)

    # Build and send reply
    reply_html = _build_reply_html(
        client_name=client_name,
        role=role,
        coe=coe,
        employee_name=employee_name,
        project_id=project_id,
        candidates=top_candidates,
        rationale=rationale,
        total_evaluated=len(scored),
    )
    await _send_reply(settings, source_email, client_name, reply_html)
    _mark_replied(db, email_request_id)
    log.info("Auto-reply sent for %s to %s (%d candidates)", email_request_id, source_email, len(top_candidates))
    return True


def _mark_replied(db: Session, email_request_id: str) -> None:
    """Update email_requests status to REPLIED."""
    db.execute(text("""
        UPDATE email_requests SET status = 'REPLIED' WHERE id = CAST(:eid AS uuid)
    """), {"eid": email_request_id})
    db.commit()


def _build_reply_html(
    client_name: str,
    role: str,
    coe: str,
    employee_name: str,
    project_id: str,
    candidates: list,
    rationale: str | None,
    total_evaluated: int,
) -> str:
    """Build professional HTML reply email with candidate table."""
    rows_html = ""
    for i, c in enumerate(candidates):
        cat_color = "#059669" if c.category == "Available" else "#7c3aed"
        score_pct = round(c.total_score * 100)
        rows_html += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:13px;font-weight:500">{c.employee_id}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:13px">{c.job_name or 'Unknown'}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:13px">{c.location or '-'}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:13px;color:{cat_color};font-weight:600">{c.category}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:13px">{c.available_pct:.0f}%</td>
            <td style="padding:10px 14px;border-bottom:1px solid #f1f1f1;font-size:14px;font-weight:700;color:#19105B">{score_pct}%</td>
        </tr>"""

    context_line = ""
    if employee_name:
        context_line = f"for replacing <strong>{employee_name}</strong> "
    if project_id:
        context_line += f"on project <strong>{project_id}</strong>"

    rationale_block = ""
    if rationale:
        rationale_block = f"""
        <div style="margin:16px 0;padding:12px 16px;background:#f8f7ff;border-left:3px solid #19105B;border-radius:4px">
            <p style="margin:0;font-size:12px;color:#6b7280;font-weight:600">TOP RECOMMENDATION INSIGHT</p>
            <p style="margin:6px 0 0;font-size:13px;color:#374151;line-height:1.5">{rationale}</p>
        </div>"""

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto">
        <div style="background:#19105B;padding:24px 28px;border-radius:12px 12px 0 0">
            <h1 style="margin:0;color:#fff;font-size:18px">Re: Resource Request — {client_name}</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.7);font-size:13px">AI-Powered Recommendation &middot; RMG Engine &middot; JMan Group</p>
        </div>
        <div style="padding:28px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px">
            <p style="font-size:14px;color:#374151;margin:0 0 8px;line-height:1.6">
                Hi,<br><br>
                We've received your extension/resource request and processed it through our AI recommendation engine.
            </p>
            <p style="font-size:14px;color:#374151;margin:0 0 20px;line-height:1.6">
                Here are the top recommended candidates for <strong>{role}</strong> ({coe}) {context_line}:
            </p>

            <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
                <thead>
                    <tr style="background:#f9fafb">
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">ID</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">Title</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">Location</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">Category</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">Available</th>
                        <th style="padding:10px 14px;text-align:left;font-size:11px;color:#6b7280;text-transform:uppercase;font-weight:600">Score</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>

            {rationale_block}

            <p style="font-size:13px;color:#6b7280;margin:20px 0 0;line-height:1.5">
                <strong>{total_evaluated}</strong> employees were evaluated using skill match, semantic similarity, availability, and productivity signals.
            </p>

            <p style="font-size:13px;color:#374151;margin:16px 0 0;line-height:1.5">
                Please reach out to discuss allocation timelines and next steps.
            </p>

            <div style="margin-top:24px;padding-top:16px;border-top:1px solid #f1f1f1">
                <p style="font-size:11px;color:#9ca3af;margin:0">
                    Automated recommendation by RMG AI Engine &middot; Scores based on skill match, competency, availability &amp; productivity &middot; JMan Group
                </p>
            </div>
        </div>
    </div>"""


def _build_no_resource_html(client_name: str, role: str, coe: str, employee_name: str, project_id: str) -> str:
    """Build reply HTML when no suitable candidates are found."""
    context = ""
    if employee_name:
        context += f" for replacing {employee_name}"
    if project_id:
        context += f" on project {project_id}"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:0 auto">
        <div style="background:#19105B;padding:24px 28px;border-radius:12px 12px 0 0">
            <h1 style="margin:0;color:#fff;font-size:18px">Re: Resource Request — {client_name}</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.7);font-size:13px">AI-Powered Recommendation &middot; RMG Engine &middot; JMan Group</p>
        </div>
        <div style="padding:28px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px">
            <p style="font-size:14px;color:#374151;margin:0 0 16px;line-height:1.6">
                Hi,<br><br>
                We've received your extension/resource request for <strong>{role}</strong> ({coe}){context} and processed it through our AI engine.
            </p>

            <div style="padding:16px 20px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;margin:0 0 20px">
                <p style="margin:0;font-size:14px;color:#991b1b;font-weight:600">No suitable internal candidates available</p>
                <p style="margin:8px 0 0;font-size:13px;color:#374151;line-height:1.5">
                    All evaluated employees are either at full capacity or lack the required skill alignment for this role.
                    We recommend considering an external hire or adjacent COE redeployment.
                </p>
            </div>

            <p style="font-size:13px;color:#374151;margin:0 0 0;line-height:1.5">
                The RMG team will follow up with a detailed hiring profile and next steps.
            </p>

            <div style="margin-top:24px;padding-top:16px;border-top:1px solid #f1f1f1">
                <p style="font-size:11px;color:#9ca3af;margin:0">
                    Automated recommendation by RMG AI Engine &middot; JMan Group
                </p>
            </div>
        </div>
    </div>"""


async def _send_reply(settings, to_email: str, client_name: str, html: str) -> None:
    """Send the reply email via Azure Communication Services."""
    from azure.communication.email import EmailClient

    client = EmailClient.from_connection_string(settings.acs_connection_string)
    message = {
        "senderAddress": settings.acs_sender_email,
        "recipients": {"to": [{"address": to_email}]},
        "content": {
            "subject": f"Re: Resource Request — {client_name} | AI Recommendation",
            "html": html,
        },
    }
    poller = client.begin_send(message)
    poller.result()
