"""Load Competency_Details.xlsx → employee_competencies table.

Sheets: 'Solution Enabler ' (5 dims), 'Solution Consultant ' (3 dims), 'Senior Software Engineer' (3 dims).
Each sheet is wide: employee_id, designation, coe_dep, [dim1_text, score, dim2_text, score, ...].
"""
import pandas as pd
from psycopg2.extras import execute_values

SHEETS = {
    "Solution Enabler ": "Solutions Enabler",
    "Solution Consultant ": "Solutions Consultant",
    "Senior Software Engineer": "Senior Software Engineer",
}


def _parse_sheet(wb_path: str, sheet_name: str, role_group: str) -> list:
    df = pd.read_excel(wb_path, sheet_name=sheet_name, header=0, engine="openpyxl")
    headers = list(df.columns)

    # Columns 0,1,2 = employee_id, designation, coe_dep
    # From col 3 onwards: alternating [dim_text, score] pairs
    dim_texts = []
    score_indices = []
    for i, h in enumerate(headers[3:], start=3):
        clean = str(h).strip().lower()
        if clean.startswith("score"):
            score_indices.append(i)
        else:
            dim_texts.append((i, str(h).strip()))

    rows = []
    for _, r in df.iterrows():
        emp_id = r.iloc[0]
        designation = r.iloc[1]
        coe_dep = r.iloc[2]
        if pd.isna(emp_id):
            continue

        for dim_idx, (col_i, dim_text) in enumerate(dim_texts):
            score_col = col_i + 1  # score is always next column
            raw_response = r.iloc[col_i]
            raw_score = r.iloc[score_col] if score_col < len(r) else None

            is_demonstrated = None
            if not pd.isna(raw_response):
                is_demonstrated = str(raw_response).strip().lower() == "yes"

            score = None
            if raw_score is not None and not pd.isna(raw_score):
                try:
                    score = int(raw_score)
                except (ValueError, TypeError):
                    pass

            rows.append((
                str(emp_id),
                str(designation) if not pd.isna(designation) else None,
                role_group,
                str(coe_dep) if not pd.isna(coe_dep) else None,
                dim_idx + 1,
                dim_text,
                is_demonstrated,
                score,
            ))
    return rows


def load(conn, xlsx_path: str) -> int:
    all_rows = []
    for sheet_name, role_group in SHEETS.items():
        try:
            all_rows.extend(_parse_sheet(xlsx_path, sheet_name, role_group))
        except Exception as e:
            print(f"  Warning: could not parse sheet '{sheet_name}': {e}")

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO employee_competencies
              (employee_id, designation, role_group, coe_dep,
               dimension_index, dimension_text, is_demonstrated, score)
            VALUES %s
            """,
            all_rows,
        )
    conn.commit()
    return len(all_rows)
