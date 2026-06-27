"""Load project_details CSV → projects + project_coes tables."""
import pandas as pd
from psycopg2.extras import execute_values

EPOCH_SENTINEL = pd.Timestamp("1970-01-01")


def _parse_date(s):
    if pd.isna(s):
        return None
    try:
        d = pd.to_datetime(s, dayfirst=True)
        if d == EPOCH_SENTINEL:
            return None
        return d.date()
    except Exception:
        return None


def load(conn, csv_path: str) -> int:
    df = pd.read_csv(csv_path, na_values=["NULL", "null", ""])

    project_rows = []
    coe_rows = []

    for _, r in df.iterrows():
        pid = str(r["project_id"])
        client_id = str(r["CLIENT_ID"]) if not pd.isna(r.get("CLIENT_ID", float("nan"))) else pid.rsplit("_", 1)[0]
        project_rows.append((
            pid,
            str(r["project_key"]) if not pd.isna(r.get("project_key", float("nan"))) else None,
            client_id,
            _parse_date(r.get("project_start_date")),
            _parse_date(r.get("project_end_date")),
            r.get("type_of_project") if not pd.isna(r.get("type_of_project", float("nan"))) else None,
            str(r["project_status"]) if not pd.isna(r.get("project_status", float("nan"))) else None,
            r.get("proposition_coe") if not pd.isna(r.get("proposition_coe", float("nan"))) else None,
            str(r["reporter_id"]) if not pd.isna(r.get("reporter_id", float("nan"))) else None,
            str(r["approver_id"]) if not pd.isna(r.get("approver_id", float("nan"))) else None,
            bool(int(r["is_active_version"])) if not pd.isna(r.get("is_active_version", float("nan"))) else True,
        ))

        raw_coe = r.get("tech_coe", None)
        if not pd.isna(raw_coe) and str(raw_coe).strip().upper() != "NULL":
            for coe in str(raw_coe).split(";"):
                coe = coe.strip()
                if coe:
                    coe_rows.append((pid, coe))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO projects
              (project_id, project_key, client_id, project_start_date, project_end_date,
               type_of_project, project_status, proposition_coe,
               reporter_id, approver_id, is_active_version)
            VALUES %s
            ON CONFLICT (project_id) DO NOTHING
            """,
            project_rows,
        )
        if coe_rows:
            execute_values(
                cur,
                "INSERT INTO project_coes (project_id, coe) VALUES %s ON CONFLICT DO NOTHING",
                coe_rows,
            )
    conn.commit()
    return len(project_rows)
