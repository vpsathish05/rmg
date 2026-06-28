"""
Microsoft Graph webhook — receives real-time email notifications.

Graph first sends a GET with ?validationToken= to verify the endpoint.
Then sends POST notifications when new emails arrive.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Request, Response, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends

router = APIRouter()
log = logging.getLogger(__name__)


async def _process_notification(message_id: str, db: Session) -> None:
    """Fetch full email, extract PDF if attached, parse with GPT, store and route."""
    from app.config import settings
    from app.services.graph import get_message, get_attachment
    from app.services.email_parser import parse_email
    from sqlalchemy import text

    if not settings.graph_client_id:
        return

    try:
        msg = await get_message(
            settings.graph_tenant_id,
            settings.graph_client_id,
            settings.graph_client_secret,
            settings.graph_mailbox,
            message_id,
        )
    except Exception as e:
        log.error("Failed to fetch message %s: %s", message_id, e)
        return

    subject: str = msg.get("subject", "")
    if not subject.lower().startswith("resource request"):
        return

    body_content = (msg.get("body") or {}).get("content", "")
    sender = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "")
    received_at = msg.get("receivedDateTime")

    existing = db.execute(
        text("SELECT id FROM email_requests WHERE outlook_message_id = :mid"),
        {"mid": message_id},
    ).fetchone()
    if existing:
        return

    # Try to extract PDF attachment content
    pdf_text = None
    if msg.get("hasAttachments"):
        try:
            pdf_text = await _extract_pdf_from_email(
                settings.graph_tenant_id, settings.graph_client_id,
                settings.graph_client_secret, settings.graph_mailbox, message_id,
            )
        except Exception as e:
            log.warning("PDF extraction failed for %s: %s", message_id, e)

    # Use PDF text if available, otherwise fall back to email body
    parse_content = pdf_text if pdf_text else body_content

    try:
        parsed = await parse_email(subject, parse_content, sender)
        status = "PARSED"
    except Exception as e:
        log.error("GPT parse failed for %s: %s", message_id, e)
        parsed = None
        status = "ERROR"

    import json
    request_type_raw = (parsed or {}).get("request_type", "NEW")
    request_type = request_type_raw if request_type_raw in ("EXTEND", "CHANGE", "NEW") else "NEW"

    # Store in email_requests
    db.execute(text("""
        INSERT INTO email_requests
            (outlook_message_id, source_email, received_at, request_type,
             raw_body, parsed_json, status)
        VALUES
            (:mid, :src, :rat, :rtype, :body, :parsed, :status)
    """), {
        "mid": message_id,
        "src": sender,
        "rat": received_at,
        "rtype": request_type,
        "body": parse_content[:10000],
        "parsed": json.dumps(parsed) if parsed else None,
        "status": status,
    })
    db.commit()

    # Route NEW requests to pipeline_requests
    if status == "PARSED" and request_type == "NEW" and parsed:
        _route_new_to_pipeline(db, parsed, sender)

    log.info("Stored email request %s (type=%s, pdf=%s)", message_id, request_type, bool(pdf_text))


async def _extract_pdf_from_email(tenant: str, client_id: str, client_secret: str, mailbox: str, message_id: str) -> str | None:
    """Download PDF attachment and extract text."""
    import base64
    import io
    import pdfplumber
    from app.services.graph import get_attachments

    attachments = await get_attachments(tenant, client_id, client_secret, mailbox, message_id)
    for att in attachments:
        name = (att.get("name") or "").lower()
        if name.endswith(".pdf") and att.get("contentBytes"):
            pdf_bytes = base64.b64decode(att["contentBytes"])
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text_parts = [page.extract_text() or "" for page in pdf.pages]
                return "\n".join(text_parts).strip()
    return None


def _route_new_to_pipeline(db: Session, parsed: dict, sender: str) -> None:
    """Insert a NEW resourcing request into pipeline_requests."""
    from sqlalchemy import text as sql_text
    db.execute(sql_text("""
        INSERT INTO pipeline_requests
            (client_name, role_code_raw, canonical_roles, allocation_pct,
             duration_weeks, required_skills, likely_start_date, probability_weight,
             status, request_type, comments, em_name)
        VALUES
            (:client, :role, :canonical, :alloc, :dur, :skills, :start,
             :prob, 'Not Resourced', 'New Request', :comments, :em)
    """), {
        "client": parsed.get("client_name"),
        "role": parsed.get("role"),
        "canonical": [parsed["role"]] if parsed.get("role") else None,
        "alloc": parsed.get("allocation_pct", 100),
        "dur": parsed.get("duration_weeks"),
        "skills": parsed.get("required_skills"),
        "start": parsed.get("start_date"),
        "prob": (parsed.get("probability_pct", 50) or 50) / 100.0,
        "comments": parsed.get("change_details") or parsed.get("comments"),
        "em": parsed.get("requested_by") or sender,
    })
    db.commit()


@router.get("")
async def validate_webhook(request: Request):
    """Graph sends GET with validationToken to verify the endpoint."""
    token = request.query_params.get("validationToken")
    if token:
        return Response(content=token, media_type="text/plain")
    return Response(status_code=200)


@router.post("")
async def receive_notification(
    request: Request,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Receive Graph change notification and process matching emails."""
    body = await request.json()
    notifications = (body or {}).get("value", [])
    for notif in notifications:
        if notif.get("clientState") != "rmg-email-webhook":
            continue
        resource_data = notif.get("resourceData") or {}
        message_id = resource_data.get("id")
        if message_id:
            background.add_task(_process_notification, message_id, db)
    return Response(status_code=202)


@router.post("/process-latest")
async def process_latest(db: Session = Depends(get_db)):
    """Manually fetch and process latest 'Resource Request' emails from the mailbox."""
    from app.config import settings
    from app.services.graph import _get_token
    import httpx

    if not settings.graph_client_id:
        return {"status": "error", "message": "Graph credentials not configured"}

    token = await _get_token(settings.graph_tenant_id, settings.graph_client_id, settings.graph_client_secret)
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"https://graph.microsoft.com/v1.0/users/{settings.graph_mailbox}/messages"
            "?$filter=startswith(subject,'Resource Request')&$top=5&$orderby=receivedDateTime desc"
            "&$select=id,subject,from,receivedDateTime,hasAttachments,body",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code >= 400:
            return {"status": "error", "message": f"Graph API {r.status_code}: {r.text[:200]}"}
        messages = r.json().get("value", [])

    processed = []
    for msg in messages:
        mid = msg["id"]
        from sqlalchemy import text as sql_text
        existing = db.execute(sql_text("SELECT id FROM email_requests WHERE outlook_message_id = :mid"), {"mid": mid}).fetchone()
        if existing:
            continue
        await _process_notification(mid, db)
        processed.append({"id": mid, "subject": msg.get("subject"), "from": ((msg.get("from") or {}).get("emailAddress") or {}).get("address")})

    return {"status": "done", "processed": len(processed), "emails": processed}
