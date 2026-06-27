"""Load project_allocation_details CSV → allocations table."""
import pandas as pd
from psycopg2.extras import execute_values

OPEN_ENDED_DATES = {"31-12-2030", "30-09-2030", "31-12-2035", "31-12-2099"}


def _parse_date(s):
    if pd.isna(s):
        return None
    try:
        return pd.to_datetime(str(s), dayfirst=True).date()
    except Exception:
        return None


def load(conn, csv_path: str) -> int:
    df = pd.read_csv(csv_path, na_values=["NULL", "null"])
    # Filter rows with blank employee_id (masked/invalid data)
    df = df[df["employee_id"].notna() & (df["employee_id"].astype(str).str.strip() != "")]

    rows = []
    for _, r in df.iterrows():
        end_raw = str(r.get("allocated_end_date", "")).strip()
        is_open_ended = end_raw in OPEN_ENDED_DATES
        rows.append((
            str(r["project_rolebased_user_id"]),
            str(r["project_id"]),
            str(r["employee_id"]),
            str(r["resourcing_status"]) if not pd.isna(r.get("resourcing_status", float("nan"))) else None,
            float(r["allocation_by_percentage"]) if not pd.isna(r.get("allocation_by_percentage", float("nan"))) else None,
            _parse_date(r.get("allocated_start_date")),
            _parse_date(r.get("allocated_end_date")),
            is_open_ended,
            bool(int(r["is_allocation_active"])) if not pd.isna(r.get("is_allocation_active", float("nan"))) else False,
            bool(int(r["is_active_version"])) if not pd.isna(r.get("is_active_version", float("nan"))) else True,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO allocations
              (id, project_id, employee_id, resourcing_status, allocation_pct,
               start_date, end_date, is_open_ended, is_active, is_active_version)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            rows,
        )
    conn.commit()
    return len(rows)
