"""Microsoft Graph API client — email subscription + message fetch."""
from __future__ import annotations
import httpx
from datetime import datetime, timedelta, timezone

_GRAPH = "https://graph.microsoft.com/v1.0"
_TOKEN_BASE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


async def _get_token(tenant: str, client_id: str, client_secret: str) -> str:
    url = _TOKEN_BASE.format(tenant=tenant)
    async with httpx.AsyncClient() as c:
        r = await c.post(url, data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        })
        r.raise_for_status()
        return r.json()["access_token"]


async def create_subscription(
    tenant: str, client_id: str, client_secret: str,
    mailbox: str, notification_url: str,
) -> dict:
    token = await _get_token(tenant, client_id, client_secret)
    expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_GRAPH}/subscriptions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "changeType": "created",
                "notificationUrl": notification_url,
                "resource": f"/users/{mailbox}/messages",
                "expirationDateTime": expiry,
                "clientState": "rmg-email-webhook",
            },
        )
        r.raise_for_status()
        return r.json()


async def renew_subscription(
    tenant: str, client_id: str, client_secret: str, subscription_id: str,
) -> None:
    token = await _get_token(tenant, client_id, client_secret)
    expiry = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    async with httpx.AsyncClient() as c:
        await c.patch(
            f"{_GRAPH}/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"expirationDateTime": expiry},
        )


async def get_message(
    tenant: str, client_id: str, client_secret: str,
    mailbox: str, message_id: str,
) -> dict:
    token = await _get_token(tenant, client_id, client_secret)
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{_GRAPH}/users/{mailbox}/messages/{message_id}"
            "?$select=subject,from,receivedDateTime,body,hasAttachments",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()



async def send_email(
    tenant: str, client_id: str, client_secret: str,
    mailbox: str, to_email: str, subject: str, body_html: str,
) -> dict:
    """Send an email via Microsoft Graph on behalf of the mailbox."""
    token = await _get_token(tenant, client_id, client_secret)
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{_GRAPH}/users/{mailbox}/sendMail",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "message": {
                    "subject": subject,
                    "body": {"contentType": "HTML", "content": body_html},
                    "toRecipients": [{"emailAddress": {"address": to_email}}],
                },
                "saveToSentItems": True,
            },
        )
        if r.status_code >= 400:
            detail = r.text
            raise Exception(f"{r.status_code} {r.reason_phrase}: {detail}")
        return {"status": "sent", "to": to_email}



async def get_attachments(
    tenant: str, client_id: str, client_secret: str,
    mailbox: str, message_id: str,
) -> list[dict]:
    """Fetch all attachments for a message."""
    token = await _get_token(tenant, client_id, client_secret)
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{_GRAPH}/users/{mailbox}/messages/{message_id}/attachments",
            headers={"Authorization": f"Bearer {token}"},
        )
        if r.status_code >= 400:
            return []
        return r.json().get("value", [])
