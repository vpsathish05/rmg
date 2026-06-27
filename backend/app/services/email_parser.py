"""Parse inbound 'Resource Request' emails using GPT-4o into structured JSON."""
from __future__ import annotations
import json
from openai import AsyncOpenAI
from app.config import settings

_SYSTEM = """You are the RMG (Resource Management Group) assistant at JMan Group.
Parse the email body and extract structured data. Return ONLY valid JSON — no commentary.

Output schema (all fields optional except request_type):
{
  "request_type": "EXTEND" | "CHANGE" | "NEW",
  "project_id": "<project code if mentioned>",
  "client_name": "<client name>",
  "employee_name": "<name of resource being extended/changed>",
  "employee_id": "<JMan employee ID if mentioned>",
  "current_end_date": "<YYYY-MM-DD>",
  "new_end_date": "<YYYY-MM-DD>",
  "allocation_pct": <number 0-100>,
  "role": "<job title / designation>",
  "coe": "<technology / COE>",
  "requested_by": "<sender name or email>",
  "change_details": "<free text describing the change>",
  "urgency": "HIGH" | "MEDIUM" | "LOW"
}

Rules:
- EXTEND = request to extend an existing resource's end date
- CHANGE = request to swap/replace/change a resource or reduce allocation
- NEW = brand new resource request (fill role/coe/allocation)
- If you cannot determine request_type, default to "NEW"
"""


async def parse_email(subject: str, body: str, sender: str) -> dict:
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = f"Subject: {subject}\nFrom: {sender}\n\nBody:\n{body}"
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"request_type": "NEW", "raw_parse_error": raw}
