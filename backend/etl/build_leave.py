"""
Build employee_leave_weeks table — detect probable leave from timesheet low-activity weeks.

Run: PYTHONPATH=. python -m etl.build_leave

Logic:
  - For each employee, calculate their personal average weekly hours (approved timesheets)
  - A week is flagged as 'leave' if hours < 25% of that employee's average
  - Only weeks with at least 1 hour logged (to distinguish leave from no-project weeks)
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import engine
from sqlalchemy import text


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS employee_leave_weeks (
    id               SERIAL PRIMARY KEY,
    employee_id      VARCHAR NOT NULL,
    week_start       DATE NOT NULL,
    week_end         DATE NOT NULL,
    hours_logged     NUMERIC(6,2) DEFAULT 0,
    avg_weekly_hours NUMERIC(6,2),
    UNIQUE (employee_id, week_start)
);
"""

DETECT_LEAVE = """
WITH weekly AS (
    SELECT
        employee_id,
        DATE_TRUNC('week', date)::DATE AS week_start,
        (DATE_TRUNC('week', date) + INTERVAL '6 days')::DATE AS week_end,
        SUM(hours) AS hours_logged
    FROM timesheets
    WHERE status = 'APPROVED'
    GROUP BY employee_id, DATE_TRUNC('week', date)
),
avg_hrs AS (
    SELECT employee_id, AVG(hours_logged) AS avg_weekly_hours
    FROM weekly
    GROUP BY employee_id
)
SELECT w.employee_id, w.week_start, w.week_end, w.hours_logged, a.avg_weekly_hours
FROM weekly w
JOIN avg_hrs a ON a.employee_id = w.employee_id
WHERE w.hours_logged > 0
  AND w.hours_logged < (a.avg_weekly_hours * 0.25)
  AND a.avg_weekly_hours > 20
"""


def main():
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLE))
        conn.commit()
        print("Table employee_leave_weeks ready.")

        rows = conn.execute(text(DETECT_LEAVE)).fetchall()
        if not rows:
            print("No leave weeks detected.")
            return

        conn.execute(text("TRUNCATE employee_leave_weeks"))
        for r in rows:
            conn.execute(text("""
                INSERT INTO employee_leave_weeks
                    (employee_id, week_start, week_end, hours_logged, avg_weekly_hours)
                VALUES (:eid, :ws, :we, :hrs, :avg)
                ON CONFLICT (employee_id, week_start) DO NOTHING
            """), {
                "eid": r.employee_id,
                "ws": r.week_start,
                "we": r.week_end,
                "hrs": float(r.hours_logged),
                "avg": float(r.avg_weekly_hours),
            })
        conn.commit()
        print(f"Inserted {len(rows)} leave-week records for "
              f"{len(set(r.employee_id for r in rows))} employees.")


if __name__ == "__main__":
    main()
