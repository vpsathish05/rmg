"""
Proactive Extension Confirmation Service.

Detects projects ending within 7 days and sends confirmation emails to EMs
every 2 days asking: No Extension / Extend / Partial.

Scheduled daily at 9am IST via APScheduler.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings

log = logging.getLogger(__name__)

# Fixed EM recipients for now
DEFAULT_RECIPIENTS = [
    "sathishkumar@jmangroup.com",
    "karthikeyan.r@jmangroup.com",
    "lejoy.j@jmangroup.com",
    "rohithraja.c@jmangroup.com",
]

# Send every 2 days within the 7-day window (Day 7, 5, 3, 1 = max 4 sends)
MAX_SENDS = 4
SEND_INTERVAL_DAYS = 2


def check_and_send_all(db: Session) -> dict:
    """
    Main entry point — called by scheduler daily.

    1. Find active projects ending within 7 days
    2. For each: check if we already sent and if it's time for a reminder
    3. Send email via ACS if needed
    4. Returns summary
    """
    projects = _find_ending_projects(db)
    sent = skipped = already_responded = 0

    for proj in projects:
        # Check if we already have a confirmation record
        existing = db.execute(text("""
            SELECT id, response, send_count, last_sent_at
            FROM extension_confirmations
            WHERE project_id = :pid
            ORDER BY created_at DESC
            LIMIT 1
        """), {"pid": proj["project_id"]}).fetchone()

        if existing and existing.response is not None:
            # Already responded — skip
            already_responded += 1
            continue

        if existing:
            # Check if enough time passed since last send (2 days)
            if existing.last_sent_at:
                hours_since = (datetime.now(timezone.utc) - existing.last_sent_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
                if hours_since < SEND_INTERVAL_DAYS * 24 - 1:  # ~47 hours minimum
                    skipped += 1
                    continue

            if existing.send_count >= MAX_SENDS:
                skipped += 1
                continue

            # Send reminder
            token = db.execute(text(
                "SELECT token FROM extension_confirmations WHERE id = :id"
            ), {"id": existing.id}).scalar()
            _send_email(proj, token, existing.send_count + 1)
            db.execute(text("""
                UPDATE extension_confirmations
                SET last_sent_at = NOW(), send_count = send_count + 1
                WHERE id = :id
            """), {"id": existing.id})
            db.commit()
            sent += 1
        else:
            # First time — create record and send
            token = secrets.token_urlsafe(32)
            db.execute(text("""
                INSERT INTO extension_confirmations
                    (project_id, client_id, project_end_date, headcount, team_summary,
                     recipients, first_sent_at, last_sent_at, send_count, token)
                VALUES
                    (:project_id, :client_id, :end_date, :headcount, :team_summary,
                     :recipients, NOW(), NOW(), 1, :token)
            """), {
                "project_id": proj["project_id"],
                "client_id": proj["client_id"],
                "end_date": proj["project_end_date"],
                "headcount": proj["headcount"],
                "team_summary": proj["team_summary"],
                "recipients": DEFAULT_RECIPIENTS,
                "token": token,
            })
            db.commit()
            _send_email(proj, token, 1)
            sent += 1

    summary = {
        "projects_ending_soon": len(projects),
        "emails_sent": sent,
        "skipped": skipped,
        "already_responded": already_responded,
    }
    log.info("Extension check: %s", summary)
    return summary


def _find_ending_projects(db: Session) -> list[dict]:
    """Find active projects ending within 7 days with allocated resources."""
    rows = db.execute(text("""
        SELECT p.project_id, p.client_id, p.project_end_date, p.proposition_coe,
               COUNT(DISTINCT a.employee_id) AS headcount,
               STRING_AGG(
                   DISTINCT e.job_name || ' (' || e.canonical_role || ', ' || a.allocation_pct || '%)',
                   ' | '
               ) AS team_summary
        FROM projects p
        JOIN allocations a ON a.project_id = p.project_id AND a.is_active_version = true
            AND a.end_date >= CURRENT_DATE AND a.resourcing_status = 'BILLABLE'
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        WHERE p.is_active_version = true
          AND p.project_status = 'ACTIVE'
          AND p.project_end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
          AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        GROUP BY p.project_id, p.client_id, p.project_end_date, p.proposition_coe
        ORDER BY p.project_end_date
    """)).fetchall()

    return [
        {
            "project_id": r.project_id,
            "client_id": r.client_id,
            "project_end_date": r.project_end_date,
            "proposition_coe": r.proposition_coe,
            "headcount": int(r.headcount),
            "team_summary": r.team_summary,
        }
        for r in rows
    ]


def _send_email(project: dict, token: str, send_number: int) -> bool:
    """Send extension confirmation email via ACS."""
    if not settings.acs_connection_string:
        log.warning("ACS not configured — skipping email for %s", project["project_id"])
        return False

    days_remaining = (project["project_end_date"] - datetime.now().date()).days
    base_url = settings.webhook_base_url

    # Build team table rows
    team_rows_html = ""
    if project["team_summary"]:
        for idx, member in enumerate(project["team_summary"].split(" | ")[:10], 1):
            bg = "#f9fafb" if idx % 2 == 0 else "#ffffff"
            team_rows_html += f'<tr style="background:{bg}"><td style="padding:10px 16px;font-size:13px;color:#19105B;border-bottom:1px solid #f1f1f5">{member}</td></tr>'

    # Subject and urgency based on send number
    if send_number == 1:
        subject = f"Action Required: Project Extension Confirmation — {project['client_id']}"
        urgency_banner = ""
    elif send_number == 2:
        subject = f"Reminder: Project Extension Confirmation — {project['client_id']}"
        urgency_banner = '<div style="background:#3411A310;border-left:4px solid #3411A3;padding:12px 16px;margin-bottom:20px;font-size:12px;color:#3411A3;font-weight:600">Reminder: We have not yet received your response regarding this project extension.</div>'
    elif send_number >= 3:
        subject = f"Urgent: Project Extension Confirmation Required — {project['client_id']}"
        urgency_banner = f'<div style="background:#FF619610;border-left:4px solid #FF6196;padding:12px 16px;margin-bottom:20px;font-size:12px;color:#A6265E;font-weight:600">Urgent: This project ends in {days_remaining} day{"s" if days_remaining != 1 else ""}. Please confirm the extension status immediately.</div>'
    else:
        subject = f"Action Required: Project Extension Confirmation — {project['client_id']}"
        urgency_banner = ""

    body_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;background:#ffffff">
        <!-- Header -->
        <div style="background:#19105B;padding:24px 32px">
            <table style="width:100%"><tr>
                <td><span style="font-size:22px;font-weight:900;color:#ffffff;letter-spacing:-0.5px">J</span><span style="font-size:14px;font-weight:700;color:#ffffff;margin-left:8px">JMAN GROUP</span></td>
                <td style="text-align:right"><span style="font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:1px">SapienSync</span></td>
            </tr></table>
        </div>

        <!-- Body -->
        <div style="padding:32px;border:1px solid #e5e7eb;border-top:none">
            {urgency_banner}

            <h2 style="font-size:18px;font-weight:700;color:#19105B;margin:0 0 8px">Project Extension Confirmation</h2>
            <p style="font-size:13px;color:#6b7280;margin:0 0 24px">Please review and confirm the extension status for the project below.</p>

            <!-- Project Details -->
            <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
                <tr>
                    <td style="padding:10px 16px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;width:140px;border-bottom:1px solid #f1f1f5">Client</td>
                    <td style="padding:10px 16px;background:#f9fafb;font-size:14px;font-weight:700;color:#19105B;border-bottom:1px solid #f1f1f5">{project['client_id']}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #f1f1f5">Project</td>
                    <td style="padding:10px 16px;font-size:13px;color:#374151;border-bottom:1px solid #f1f1f5">{project['project_id']}</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #f1f1f5">End Date</td>
                    <td style="padding:10px 16px;background:#f9fafb;font-size:14px;font-weight:700;color:#FF6196;border-bottom:1px solid #f1f1f5">{project['project_end_date'].strftime('%d %B %Y')} ({days_remaining} day{"s" if days_remaining != 1 else ""} remaining)</td>
                </tr>
                <tr>
                    <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #f1f1f5">Headcount</td>
                    <td style="padding:10px 16px;font-size:13px;color:#374151;border-bottom:1px solid #f1f1f5">{project['headcount']} resource{"s" if project['headcount'] != 1 else ""}</td>
                </tr>
                {f'<tr><td style="padding:10px 16px;background:#f9fafb;font-size:12px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #f1f1f5">COE</td><td style="padding:10px 16px;background:#f9fafb;font-size:13px;color:#374151;border-bottom:1px solid #f1f1f5">{project["proposition_coe"]}</td></tr>' if project.get("proposition_coe") else ""}
            </table>

            <!-- Team -->
            <p style="font-size:12px;font-weight:700;color:#19105B;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 8px">Currently Allocated Team</p>
            <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;margin-bottom:28px">
                <thead>
                    <tr style="background:#19105B">
                        <th style="padding:10px 16px;text-align:left;font-size:11px;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px">Name (Role, Allocation)</th>
                    </tr>
                </thead>
                <tbody>{team_rows_html}</tbody>
            </table>

            <!-- Action Required -->
            <p style="font-size:14px;font-weight:700;color:#19105B;margin:0 0 16px">What is the plan for this project?</p>
            <p style="font-size:12px;color:#6b7280;margin:0 0 20px">Please select one of the options below. Your response will update the resource planning system immediately.</p>

            <!-- Buttons -->
            <table style="width:100%;border-collapse:collapse;margin-bottom:28px"><tr>
                <td style="padding:0 6px 8px 0">
                    <a href="{base_url}/api/rmg/extension-response?token={token}&response=no_extension"
                       style="display:block;padding:14px 20px;background:#19105B;color:#ffffff;font-size:13px;font-weight:700;text-decoration:none;text-align:center;border-radius:6px">
                        No Extension
                    </a>
                    <p style="font-size:10px;color:#6b7280;text-align:center;margin:6px 0 0">All resources become available</p>
                </td>
                <td style="padding:0 3px 8px 3px">
                    <a href="{base_url}/api/rmg/extension-response?token={token}&response=extend"
                       style="display:block;padding:14px 20px;background:#3411A3;color:#ffffff;font-size:13px;font-weight:700;text-decoration:none;text-align:center;border-radius:6px">
                        Extend (Full Team)
                    </a>
                    <p style="font-size:10px;color:#6b7280;text-align:center;margin:6px 0 0">Entire team continues</p>
                </td>
                <td style="padding:0 0 8px 6px">
                    <a href="{base_url}/api/rmg/extension-response?token={token}&response=partial"
                       style="display:block;padding:14px 20px;background:#FF6196;color:#ffffff;font-size:13px;font-weight:700;text-decoration:none;text-align:center;border-radius:6px">
                        Partial Extension
                    </a>
                    <p style="font-size:10px;color:#6b7280;text-align:center;margin:6px 0 0">Select who stays</p>
                </td>
            </tr></table>

            <!-- Note -->
            <div style="border-top:1px solid #f1f1f5;padding-top:16px">
                <p style="font-size:11px;color:#9ca3af;margin:0;line-height:1.6">
                    If no response is received, resources will be treated as available for new projects after the project end date.
                    This is notification {send_number} of {MAX_SENDS}.
                </p>
            </div>
        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 32px;border:1px solid #e5e7eb;border-top:none">
            <p style="font-size:11px;color:#9ca3af;margin:0;text-align:center">
                Jman Group · SapienSync Resource Management · This is an automated notification
            </p>
        </div>
    </div>"""

    try:
        from azure.communication.email import EmailClient
        client = EmailClient.from_connection_string(settings.acs_connection_string)
        message = {
            "senderAddress": settings.acs_sender_email,
            "recipients": {
                "to": [{"address": e} for e in DEFAULT_RECIPIENTS]
            },
            "content": {
                "subject": subject,
                "html": body_html,
            },
        }
        poller = client.begin_send(message)
        poller.result()
        log.info("Extension email sent for %s (send #%d)", project["project_id"], send_number)
        return True
    except Exception as e:
        log.error("Failed to send extension email for %s: %s", project["project_id"], e)
        return False


def get_confirmation_status(db: Session, project_id: str) -> dict | None:
    """Get the current confirmation status for a project."""
    row = db.execute(text("""
        SELECT id, project_id, client_id, project_end_date, headcount, team_summary,
               send_count, first_sent_at, last_sent_at, response, responded_at,
               responded_by, staying_employee_ids, new_end_date, notes, token
        FROM extension_confirmations
        WHERE project_id = :pid
        ORDER BY created_at DESC
        LIMIT 1
    """), {"pid": project_id}).fetchone()

    if not row:
        return None

    return {
        "id": row.id,
        "project_id": row.project_id,
        "client_id": row.client_id,
        "project_end_date": row.project_end_date.isoformat() if row.project_end_date else None,
        "headcount": row.headcount,
        "team_summary": row.team_summary,
        "send_count": row.send_count,
        "first_sent_at": row.first_sent_at.isoformat() if row.first_sent_at else None,
        "last_sent_at": row.last_sent_at.isoformat() if row.last_sent_at else None,
        "response": row.response,
        "responded_at": row.responded_at.isoformat() if row.responded_at else None,
        "responded_by": row.responded_by,
        "staying_employee_ids": row.staying_employee_ids,
        "new_end_date": row.new_end_date.isoformat() if row.new_end_date else None,
        "notes": row.notes,
    }


def get_all_confirmations(db: Session) -> list[dict]:
    """Get all recent extension confirmations for the UI."""
    rows = db.execute(text("""
        SELECT id, project_id, client_id, project_end_date, headcount, team_summary,
               send_count, first_sent_at, last_sent_at, response, responded_at,
               staying_employee_ids, new_end_date
        FROM extension_confirmations
        ORDER BY project_end_date ASC, created_at DESC
    """)).fetchall()

    return [
        {
            "id": r.id,
            "project_id": r.project_id,
            "client_id": r.client_id,
            "project_end_date": r.project_end_date.isoformat() if r.project_end_date else None,
            "headcount": r.headcount,
            "team_summary": r.team_summary,
            "send_count": r.send_count,
            "first_sent_at": r.first_sent_at.isoformat() if r.first_sent_at else None,
            "last_sent_at": r.last_sent_at.isoformat() if r.last_sent_at else None,
            "response": r.response,
            "responded_at": r.responded_at.isoformat() if r.responded_at else None,
            "staying_employee_ids": r.staying_employee_ids,
            "new_end_date": r.new_end_date.isoformat() if r.new_end_date else None,
        }
        for r in rows
    ]


def get_locked_employee_ids(db: Session) -> set[str]:
    """
    Get employee IDs that are locked from recommendations due to extension confirmations.

    Locked = on a project where response is 'extend' (all stay)
             OR listed in staying_employee_ids (partial — these specific people stay)
    """
    # Projects where full team is extending
    extend_projects = db.execute(text("""
        SELECT project_id FROM extension_confirmations
        WHERE response = 'extend'
    """)).fetchall()

    locked = set()

    # Get all employees on fully-extending projects
    if extend_projects:
        project_ids = [r.project_id for r in extend_projects]
        emp_rows = db.execute(text("""
            SELECT DISTINCT a.employee_id
            FROM allocations a
            WHERE a.project_id = ANY(:pids)
              AND a.is_active_version = true
              AND a.resourcing_status = 'BILLABLE'
              AND a.end_date >= CURRENT_DATE
        """), {"pids": project_ids}).fetchall()
        locked.update(r.employee_id for r in emp_rows)

    # Get employees specifically listed in partial extensions
    partial_rows = db.execute(text("""
        SELECT staying_employee_ids FROM extension_confirmations
        WHERE response = 'partial' AND staying_employee_ids IS NOT NULL
    """)).fetchall()

    for r in partial_rows:
        if r.staying_employee_ids:
            locked.update(r.staying_employee_ids)

    return locked
