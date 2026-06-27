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
    """Fetch full email, parse with GPT, store in email_requests."""
    from app.config import settings
    from app.services.graph import get_message
    from app.services.email_parser import parse_email
    from sqlalchemy import text

    # Skip if Graph credentials not configured
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
    # Only process "Resource Request" emails
    if not subject.lower().startswith("resource request"):
        return

    body_content = (msg.get("body") or {}).get("content", "")
    sender = ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "")
    received_at = msg.get("receivedDateTime")

    # Already processed?
    existing = db.execute(
        text("SELECT id FROM email_requests WHERE outlook_message_id = :mid"),
        {"mid": message_id},
    ).fetchone()
    if existing:
        return

    # Parse with GPT
    try:
        parsed = await parse_email(subject, body_content, sender)
        status = "PARSED"
    except Exception as e:
        log.error("GPT parse failed for %s: %s", message_id, e)
        parsed = None
        status = "ERROR"

    import json

    request_type_raw = (parsed or {}).get("request_type", "NEW")
    request_type = request_type_raw if request_type_raw in ("EXTEND", "CHANGE") else None

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
        "body": body_content[:10000],
        "parsed": json.dumps(parsed) if parsed else None,
        "status": status,
    })
    db.commit()
    log.info("Stored email request %s (type=%s)", message_id, request_type)


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
        # Validate client state to avoid spoofed calls
        if notif.get("clientState") != "rmg-email-webhook":
            continue
        resource_data = notif.get("resourceData") or {}
        message_id = resource_data.get("id")
        if message_id:
            background.add_task(_process_notification, message_id, db)
    return Response(status_code=202)
