"""Load employee_details CSV → employees table."""
import pandas as pd
from psycopg2.extras import execute_values

CANONICAL_ROLE_MAP = {
    "Associate Consultant": "Associate Consultant",
    "Senior Associate Consultant": "Senior Associate Consultant",
    "Consultant": "Consultant",
    "Senior Consultant": "Senior Consultant",
    "Manager": "Manager",
    "Senior Manager": "Senior Manager",
    "Associate Partner": "Associate Partner",
    "Partner": "Partner",
    "Principal": "Principal",
    "Senior Software Engineer": "Senior Software Engineer",
    "Solutions Enabler": "Solutions Enabler",
    "Solutions Consultant": "Solutions Consultant",
    "Senior Solution Consultant": "Senior Solution Consultant",
    "Engagement Manager": "Engagement Manager",
    "GTM Architect": "GTM Architect",
}

UK_US_KEYWORDS = ["London", "New York", "UK", "US", "United Kingdom", "United States"]


def _region(location: str) -> str:
    if pd.isna(location):
        return "IN"
    for kw in UK_US_KEYWORDS:
        if kw.lower() in str(location).lower():
            return "UK_US"
    return "IN"


def load(conn, csv_path: str) -> int:
    df = pd.read_csv(csv_path, na_values=["NULL", "null", ""])
    # Keep ALL employees including those with NULL job_name (inactive stubs);
    # they are referenced by allocations, skills, and timesheets.

    def parse_date(s):
        if pd.isna(s):
            return None
        try:
            return pd.to_datetime(s, dayfirst=True).date()
        except Exception:
            return None

    rows = []
    for _, r in df.iterrows():
        emp_id = r.get("employee_id")
        if pd.isna(emp_id):
            continue
        rows.append((
            str(emp_id),
            r.get("location") if not pd.isna(r.get("location", float("nan"))) else None,
            parse_date(r.get("date_of_join")),
            parse_date(r.get("date_of_resignation")),
            r.get("job_name") if not pd.isna(r.get("job_name", float("nan"))) else None,
            r.get("department_name") if not pd.isna(r.get("department_name", float("nan"))) else None,
            str(r["manager_id"]) if not pd.isna(r.get("manager_id", float("nan"))) else None,
            bool(int(r["account_status"])) if not pd.isna(r.get("account_status", float("nan"))) else False,
            CANONICAL_ROLE_MAP.get(str(r.get("job_name", "")), str(r.get("job_name", ""))),
            _region(r.get("location")),
            bool(int(r["is_active_version"])) if not pd.isna(r.get("is_active_version", float("nan"))) else True,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO employees
              (employee_id, location, date_of_join, date_of_resignation,
               job_name, department_name, manager_id, account_status,
               canonical_role, hierarchy_region, is_active_version)
            VALUES %s
            ON CONFLICT (employee_id) DO NOTHING
            """,
            rows,
        )
    conn.commit()
    return len(rows)
