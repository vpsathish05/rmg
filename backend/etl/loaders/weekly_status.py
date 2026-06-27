"""Load project_weekly_status CSV → weekly_status table (71K rows, batch insert)."""
import re
import pandas as pd
from psycopg2.extras import execute_values

BATCH = 5000


def _normalize_project_id(raw: str) -> str:
    """CLIENT_661-683 → CLIENT_661_683 (hyphen between digits → underscore)."""
    if pd.isna(raw):
        return None
    return re.sub(r"(\d)-(\d)", r"\1_\2", str(raw))


def _parse_date(s):
    if pd.isna(s):
        return None
    try:
        return pd.to_datetime(str(s), dayfirst=True).date()
    except Exception:
        return None


def _parse_ts(s):
    if pd.isna(s):
        return None
    try:
        return pd.to_datetime(str(s), dayfirst=True)
    except Exception:
        return None


def load(conn, csv_path: str) -> int:
    df = pd.read_csv(csv_path, na_values=["NULL", "null", ""])
    total = 0

    with conn.cursor() as cur:
        batch = []
        for _, r in df.iterrows():
            batch.append((
                str(r["wsr_key"]),
                str(r["wsr_id"]) if not pd.isna(r.get("wsr_id", float("nan"))) else None,
                _normalize_project_id(r.get("project_id_masked")),
                _parse_date(r.get("week_start_date")),
                _parse_date(r.get("week_end_date")),
                str(r["scope_status"]) if not pd.isna(r.get("scope_status", float("nan"))) else "NO_COLOR",
                str(r["schedule_status"]) if not pd.isna(r.get("schedule_status", float("nan"))) else "NO_COLOR",
                str(r["quality_status"]) if not pd.isna(r.get("quality_status", float("nan"))) else "NO_COLOR",
                str(r["csat_status"]) if not pd.isna(r.get("csat_status", float("nan"))) else "NO_COLOR",
                str(r["team_status"]) if not pd.isna(r.get("team_status", float("nan"))) else "NO_COLOR",
                _parse_ts(r.get("created_at")),
                _parse_ts(r.get("updated_at")),
            ))
            if len(batch) >= BATCH:
                execute_values(
                    cur,
                    """
                    INSERT INTO weekly_status
                      (id, wsr_id, project_id, week_start, week_end,
                       scope_status, schedule_status, quality_status,
                       csat_status, team_status, created_at, updated_at)
                    VALUES %s
                    ON CONFLICT (id) DO NOTHING
                    """,
                    batch,
                )
                total += len(batch)
                batch = []

        if batch:
            execute_values(
                cur,
                """
                INSERT INTO weekly_status
                  (id, wsr_id, project_id, week_start, week_end,
                   scope_status, schedule_status, quality_status,
                   csat_status, team_status, created_at, updated_at)
                VALUES %s
                ON CONFLICT (id) DO NOTHING
                """,
                batch,
            )
            total += len(batch)

    conn.commit()
    return total
