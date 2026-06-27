"""Load Pipeline_Details.xlsx Forecast sheet → pipeline_requests table."""
import pandas as pd
from psycopg2.extras import execute_values

DEAL_STAGE_PROBABILITY = {
    "sow signed":           1.0,
    "deal won":             0.9,
    "closed won":           0.9,
    "scoping approval":     0.7,
    "contract in progress": 0.6,
    "proposal submitted":   0.5,
    "proposal in progress": 0.4,
    "discovery":            0.3,
    "qualification":        0.2,
}


def _prob(deal_stage: str) -> float:
    if pd.isna(deal_stage):
        return 0.5
    key = str(deal_stage).strip().lower()
    for pattern, prob in DEAL_STAGE_PROBABILITY.items():
        if pattern in key:
            return prob
    return 0.5


def _parse_date(v) -> "date | None":
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date()
    try:
        return pd.to_datetime(str(v), dayfirst=True).date()
    except Exception:
        return None


def _sow(v) -> bool:
    if pd.isna(v):
        return False
    return str(v).strip().lower() in ("yes", "true", "1")


def load(conn, xlsx_path: str, role_mapping: dict) -> int:
    """
    role_mapping: dict[raw_code → {canonical_roles, always_best_match}]
    """
    df = pd.read_excel(xlsx_path, sheet_name="Forecast", header=0, engine="openpyxl")

    cols = [
        "Cluster", "Request Received", "Original Requested Start Date",
        "Request Type", "Client Priority", "Client", "EM",
        "Likely Start Date", "Start Date Confirmed", "Number of Weeks",
        "Deal Stage\n(HubSpot)", "Solution", "Priority", "Status",
        "Resources Requested", "%", "Resource Recommended", "% Available",
        "Skillset", "Skillset Match (Complete / Partial / No)",
        "SOW Signed", "Comments",
    ]
    # Normalise columns — take whatever is there
    df.columns = [str(c).strip() for c in df.columns]

    rows = []
    current_client = current_cluster = current_priority = current_deal_stage = current_solution = current_em = None
    current_sow = None
    current_received = current_orig_start = None

    for _, r in df.iterrows():
        # Carry-forward group fields (rows with same deal but multiple roles)
        if not pd.isna(r.get("Client", None)):
            current_client = str(r["Client"]).strip()
        if not pd.isna(r.get("Cluster", None)):
            try:
                current_cluster = int(r["Cluster"])
            except Exception:
                pass
        if not pd.isna(r.get("Client Priority", None)):
            current_priority = str(r["Client Priority"]).strip()
        col_ds = next((c for c in df.columns if c.startswith("Deal Stage")), None)
        if col_ds and not pd.isna(r.get(col_ds, None)):
            current_deal_stage = str(r[col_ds]).strip()
        if not pd.isna(r.get("Solution", None)):
            current_solution = str(r["Solution"]).strip()
        if not pd.isna(r.get("EM", None)):
            current_em = str(r["EM"]).strip()
        if not pd.isna(r.get("SOW Signed", None)):
            current_sow = _sow(r["SOW Signed"])
        if not pd.isna(r.get("Request Received", None)):
            current_received = _parse_date(r["Request Received"])
        if not pd.isna(r.get("Original Requested Start Date", None)):
            current_orig_start = _parse_date(r["Original Requested Start Date"])

        role_raw = str(r.get("Resources Requested", "")).strip()
        if not role_raw or role_raw.lower() in ("nan", "none", ""):
            continue

        rm = role_mapping.get(role_raw, {})
        canonical = rm.get("canonical_roles")
        always_bm = rm.get("always_best_match", False)

        pct_val = r.get("%", None)
        alloc_pct = None
        if not pd.isna(pct_val):
            try:
                alloc_pct = float(pct_val)
            except Exception:
                pass

        rows.append((
            current_cluster,
            current_client,
            current_priority,
            current_deal_stage,
            current_solution,
            str(r.get("Priority", "")).strip() or None,
            str(r.get("Status", "")).strip() or None,
            current_sow,
            _prob(current_deal_stage),
            role_raw,
            canonical,
            always_bm,
            alloc_pct,
            str(r.get("Skillset", "")).strip() or None,
            str(r.get("Skillset Match (Complete / Partial / No)", "")).strip() or None,
            _parse_date(r.get("Likely Start Date")),
            str(r.get("Start Date Confirmed", "")).strip().lower() == "yes",
            (lambda v: int(v) if not pd.isna(v) and str(v).strip().isdigit() else None)(r.get("Number of Weeks")),
            str(r.get("Request Type", "")).strip() or None,
            str(r.get("Comments", "")).strip() or None,
            current_received,
            current_orig_start,
            current_em,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO pipeline_requests
              (cluster, client_name, client_priority, deal_stage, solution,
               priority, status, sow_signed, probability_weight,
               role_code_raw, canonical_roles, always_best_match,
               allocation_pct, required_skills, skillset_match,
               likely_start_date, start_date_confirmed, duration_weeks,
               request_type, comments, request_received,
               original_requested_start_date, em_name)
            VALUES %s
            """,
            rows,
        )
    conn.commit()
    return len(rows)
