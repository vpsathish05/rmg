"""Load timesheet_details_2026 CSV → timesheets table (128K rows, batch insert)."""
import pandas as pd
from psycopg2.extras import execute_values

BATCH = 5000


def _parse_date(s):
    if pd.isna(s):
        return None
    try:
        return pd.to_datetime(str(s), dayfirst=True).date()
    except Exception:
        return None


def load(conn, csv_path: str) -> int:
    df = pd.read_csv(csv_path, na_values=["NULL", "null", ""])
    # Filter out malformed rows (employee_id='0' or non-EMP values)
    df = df[df["employee_id"].astype(str).str.match(r"^EMP\d+$", na=False)]
    total = 0

    with conn.cursor() as cur:
        batch = []
        for _, r in df.iterrows():
            batch.append((
                str(r["timesheet_surrogate_key"]),
                str(r["employee_id"]) if not pd.isna(r.get("employee_id", float("nan"))) else None,
                str(r["timesheet_id"]) if not pd.isna(r.get("timesheet_id", float("nan"))) else None,
                str(r["manager_id"]) if not pd.isna(r.get("manager_id", float("nan"))) else None,
                str(r["project_id"]) if not pd.isna(r.get("project_id", float("nan"))) else None,
                str(r["project_task_id"]) if not pd.isna(r.get("project_task_id", float("nan"))) else None,
                _parse_date(r.get("date")),
                float(r["time"]) if not pd.isna(r.get("time", float("nan"))) else None,
                str(r["status"]) if not pd.isna(r.get("status", float("nan"))) else None,
                _parse_date(r.get("submitted_on")),
                _parse_date(r.get("created_at")),
                _parse_date(r.get("updated_at")),
            ))
            if len(batch) >= BATCH:
                execute_values(
                    cur,
                    """
                    INSERT INTO timesheets
                      (surrogate_key, employee_id, timesheet_id, manager_id,
                       project_id, project_task_id, date, hours, status,
                       submitted_on, created_at, updated_at)
                    VALUES %s
                    ON CONFLICT (surrogate_key) DO NOTHING
                    """,
                    batch,
                )
                total += len(batch)
                batch = []

        if batch:
            execute_values(
                cur,
                """
                INSERT INTO timesheets
                  (surrogate_key, employee_id, timesheet_id, manager_id,
                   project_id, project_task_id, date, hours, status,
                   submitted_on, created_at, updated_at)
                VALUES %s
                ON CONFLICT (surrogate_key) DO NOTHING
                """,
                batch,
            )
            total += len(batch)

    conn.commit()
    return total
