"""Master ETL runner — loads all 7 source files into Neon.

Usage (from backend/ with venv active):
    python -m etl.load_all

Reads DATABASE_URL from .env via python-dotenv.
"""
import os
import sys
import time
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from etl.loaders import (
    employees,
    projects,
    allocations,
    timesheets,
    weekly_status,
    skills,
    competencies,
    pipeline,
    role_mapping,
)

DOCS = Path(__file__).parent.parent.parent / "docs"

FILES = {
    "employees":     DOCS / "01. 260624 employee_details.csv",
    "projects":      DOCS / "02. 260624 project_details.csv",
    "allocations":   DOCS / "03. 260623_Project_Allocation_Details.csv",
    "timesheets":    DOCS / "04. 260624 timesheet_details_2026.csv.csv",
    "weekly_status": DOCS / "09. 260624_Project_Weekly_Status_Details.csv.csv",
    "skills":        DOCS / "05. 260624 Skill_Data.xlsx",
    "competencies":  DOCS / "06. 260623_Competency_Details.xlsx",
    "pipeline":      DOCS / "07. 260624_Pipeline_Details.xlsx",
}


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("ERROR: DATABASE_URL not set — create backend/.env from .env.example")

    print("Connecting to Neon …")
    conn = psycopg2.connect(db_url)
    print("Connected.\n")

    steps = [
        ("role_mapping",  lambda: role_mapping.load(conn)),
        ("employees",     lambda: employees.load(conn, str(FILES["employees"]))),
        ("projects",      lambda: projects.load(conn, str(FILES["projects"]))),
        ("allocations",   lambda: allocations.load(conn, str(FILES["allocations"]))),
        ("timesheets",    lambda: timesheets.load(conn, str(FILES["timesheets"]))),
        ("weekly_status", lambda: weekly_status.load(conn, str(FILES["weekly_status"]))),
        ("skills",        lambda: skills.load(conn, str(FILES["skills"]))),
        ("competencies",  lambda: competencies.load(conn, str(FILES["competencies"]))),
        ("pipeline",      lambda: _load_pipeline(conn)),
    ]

    results = {}
    for name, fn in steps:
        print(f"  Loading {name} …", end=" ", flush=True)
        t0 = time.time()
        try:
            count = fn()
            elapsed = time.time() - t0
            print(f"{count:,} rows  ({elapsed:.1f}s)")
            results[name] = count
        except Exception as exc:
            print(f"FAILED — {exc}")
            conn.rollback()
            results[name] = f"ERROR: {exc}"

    conn.close()
    print("\n── ETL summary ──────────────────────────────")
    for name, val in results.items():
        print(f"  {name:<18} {val}")
    print("─────────────────────────────────────────────")


def _load_pipeline(conn):
    # Build role_mapping lookup from DB
    with conn.cursor() as cur:
        cur.execute("SELECT raw_code, canonical_roles, always_best_match FROM role_mapping")
        rm = {
            row[0]: {"canonical_roles": row[1], "always_best_match": row[2]}
            for row in cur.fetchall()
        }
    return pipeline.load(conn, str(FILES["pipeline"]), rm)


if __name__ == "__main__":
    main()
