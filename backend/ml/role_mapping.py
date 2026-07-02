"""
Role Mapping — Pipeline code → standard role, location, COE.

Source: docs/pricing/Cluster_Revenue_COE_Forecast.xlsx → "Role_Mapping" sheet.

Maps pipeline role codes (e.g. "SC", "SSE", "Sol Con") to:
  - Mapped Role (matches Rate_Card)
  - Default Location (UK/IN)
  - Mapped COE (Data Engineering, Consulting, Full Stack, etc.)
  - Confidence level
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import openpyxl

from .rate_card import _DOCS_DIR, CLUSTER_FORECAST_FILE, _normalize_location


# ── Data class ──────────────────────────────────────────────────────────────

@dataclass
class RoleMapping:
    """Mapping from a pipeline role code to standard fields."""
    pipeline_code: str       # Raw code from pipeline (e.g. "SC", "SSE")
    mapped_role: str         # Standard role name (matches Rate_Card)
    default_location: str    # UK, IN, USA
    mapped_coe: str          # Centre of Excellence
    confidence: str          # High, Medium, Low + notes


# ── Parser ──────────────────────────────────────────────────────────────────

_CACHE: Optional[dict[str, RoleMapping]] = None


def _parse_role_mapping(filepath: Path) -> dict[str, RoleMapping]:
    """
    Parse Role_Mapping sheet from Cluster_Revenue_COE_Forecast.xlsx.
    
    Layout (row 3 is header):
      Col A: Pipeline Role Code
      Col B: Mapped Role (Rate_Card)
      Col C: Default Location
      Col D: Mapped COE
      Col E: Confidence
    """
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    ws = wb["Role_Mapping"]

    mappings: dict[str, RoleMapping] = {}

    for row in ws.iter_rows(min_row=4, max_row=35, values_only=True):
        code = row[0]
        mapped_role = row[1]
        location = row[2]
        coe = row[3]
        confidence = row[4] if len(row) > 4 else ""

        if not code or not mapped_role:
            continue

        code = str(code).strip()
        # Skip header row if accidentally included
        if code.lower() == "pipeline role code":
            continue
        mapped_role = str(mapped_role).strip()
        location = _normalize_location(str(location).strip()) or "IN"
        coe = str(coe).strip() if coe else "Unknown"
        confidence = str(confidence).strip() if confidence else "Unknown"

        mappings[code] = RoleMapping(
            pipeline_code=code,
            mapped_role=mapped_role,
            default_location=location,
            mapped_coe=coe,
            confidence=confidence,
        )

    wb.close()
    return mappings


def load_role_mapping(docs_dir: Optional[Path] = None) -> dict[str, RoleMapping]:
    """
    Load role mapping. Returns dict keyed by pipeline_code.
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    base = docs_dir or _DOCS_DIR
    filepath = base / CLUSTER_FORECAST_FILE

    if not filepath.exists():
        raise FileNotFoundError(f"Cluster forecast file not found: {filepath}")

    _CACHE = _parse_role_mapping(filepath)
    return _CACHE


def resolve_role(pipeline_code: str) -> Optional[RoleMapping]:
    """
    Look up a pipeline role code and return its mapping.
    Tries exact match first, then case-insensitive, then partial match.
    """
    mappings = load_role_mapping()

    # Exact match
    if pipeline_code in mappings:
        return mappings[pipeline_code]

    # Case-insensitive
    code_lower = pipeline_code.lower().strip()
    for code, mapping in mappings.items():
        if code.lower() == code_lower:
            return mapping

    # Partial match (pipeline codes can be substrings)
    for code, mapping in mappings.items():
        if code_lower in code.lower() or code.lower() in code_lower:
            return mapping

    return None


def get_coe_for_role(pipeline_code: str) -> Optional[str]:
    """Get the COE for a pipeline role code."""
    mapping = resolve_role(pipeline_code)
    return mapping.mapped_coe if mapping else None


def get_all_coes() -> list[str]:
    """Get all unique COEs from the role mapping."""
    mappings = load_role_mapping()
    return sorted(set(m.mapped_coe for m in mappings.values()))


def get_all_mappings() -> list[RoleMapping]:
    """Return all role mappings as a list."""
    return list(load_role_mapping().values())


def clear_cache():
    """Clear the cached role mapping."""
    global _CACHE
    _CACHE = None


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mappings = load_role_mapping()
    print(f"Loaded {len(mappings)} role mappings\n")
    print(f"{'Code':<20} {'Mapped Role':<30} {'Loc':<5} {'COE':<25} {'Confidence'}")
    print("-" * 110)
    for code, m in sorted(mappings.items()):
        print(f"{code:<20} {m.mapped_role:<30} {m.default_location:<5} {m.mapped_coe:<25} {m.confidence}")

    print(f"\nUnique COEs: {get_all_coes()}")
