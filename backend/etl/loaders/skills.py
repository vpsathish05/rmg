"""Load Skill_Data.xlsx → employee_skills table.

Score = 0 interpretation per (employee_id, COE) group:
  - If group has ANY score > 0  → is_assessed=True,  keep score as-is
  - If ALL scores == 0 in group → is_assessed=False, store score as NULL
"""
import pandas as pd
from psycopg2.extras import execute_values


def load(conn, xlsx_path: str) -> int:
    df = pd.read_excel(xlsx_path, sheet_name="Sheet2", engine="openpyxl")
    df.columns = ["employee_id", "designation", "coe", "coe_skill", "skill_category", "sub_skill", "experience_band", "score"]
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)

    # Determine is_assessed per (employee_id, coe) group
    group_max = df.groupby(["employee_id", "coe"])["score"].transform("max")
    df["is_assessed"] = group_max > 0
    # When unassessed, set score to None
    df.loc[~df["is_assessed"], "score"] = None

    rows = []
    for _, r in df.iterrows():
        rows.append((
            str(r["employee_id"]) if not pd.isna(r["employee_id"]) else None,
            str(r["designation"]) if not pd.isna(r["designation"]) else None,
            str(r["coe"]) if not pd.isna(r["coe"]) else None,
            str(r["coe_skill"]) if not pd.isna(r["coe_skill"]) else None,
            str(r["skill_category"]) if not pd.isna(r["skill_category"]) else None,
            str(r["sub_skill"]) if not pd.isna(r["sub_skill"]) else None,
            str(r["experience_band"]) if not pd.isna(r["experience_band"]) else None,
            int(r["score"]) if r["score"] is not None and not pd.isna(r["score"]) else None,
            bool(r["is_assessed"]),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO employee_skills
              (employee_id, designation, coe, coe_skill, skill_category,
               sub_skill, experience_band, score, is_assessed)
            VALUES %s
            """,
            rows,
        )
    conn.commit()
    return len(rows)
