"""Seed role_mapping table with all 27 canonical role-code mappings."""
from psycopg2.extras import execute_values

ROLE_MAPPING_ROWS = [
    ("AC",                  ["Associate Consultant"],                                                False, False, None),
    ("AC (UK)",             ["Associate Consultant"],                                                False, False, "UK variant"),
    ("AP",                  ["Associate Partner"],                                                   False, False, None),
    ("AP/P",                ["Associate Partner", "Partner"],                                        True,  False, None),
    ("C",                   ["Consultant"],                                                          False, False, None),
    ("C/SAC/AC",            ["Consultant", "Senior Associate Consultant", "Associate Consultant"],   True,  False, None),
    ("EM",                  ["Engagement Manager"],                                                  False, True,  "Standalone functional role — no employee grade match. Always Best Match."),
    ("Enabler",             ["Solutions Enabler"],                                                   False, False, None),
    ("GTM Architect",       ["GTM Architect"],                                                       False, True,  "Standalone specialized role — no employee grade match. Always Best Match."),
    ("M",                   ["Manager"],                                                             False, False, None),
    ("P",                   ["Principal"],                                                           False, False, None),
    ("PA",                  ["Principal"],                                                           False, False, "Principal Architect = Principal"),
    ("SAC",                 ["Senior Associate Consultant"],                                         False, False, None),
    ("SAC - C",             ["Senior Associate Consultant", "Consultant"],                           True,  False, None),
    ("SAC or AC",           ["Senior Associate Consultant", "Associate Consultant"],                 True,  False, None),
    ("SAC/AC",              ["Senior Associate Consultant", "Associate Consultant"],                 True,  False, None),
    ("SC",                  ["Senior Consultant"],                                                   False, False, None),
    ("SC (EM)",             ["Senior Consultant"],                                                   False, False, "EM is functional overlay, grade = Senior Consultant"),
    ("SC or C - EM",        ["Senior Consultant", "Consultant"],                                     True,  False, None),
    ("SE",                  ["Solutions Enabler"],                                                   False, False, None),
    ("SSE",                 ["Senior Software Engineer"],                                            False, False, None),
    ("SSE  or SE",          ["Senior Software Engineer", "Solutions Enabler"],                       True,  False, None),
    ("Snr Sol Con",         ["Senior Solution Consultant"],                                          False, False, "= Manager"),
    ("Sol Con",             ["Senior Consultant"],                                                   False, False, "= Solution Consultant"),
    ("Sol Con/Enabler/SSE", ["Senior Consultant", "Solutions Enabler", "Senior Software Engineer"],  True,  False, None),
    ("Sr DS SME",           None,                                                                    False, False, "IGNORED — excluded from recommendation engine"),
    ("Sr Sol Con",          ["Senior Solution Consultant"],                                          False, False, "= Manager"),
]


def load(conn) -> int:
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO role_mapping (raw_code, canonical_roles, is_compound, always_best_match, notes)
            VALUES %s
            ON CONFLICT (raw_code) DO NOTHING
            """,
            ROLE_MAPPING_ROWS,
        )
    conn.commit()
    return len(ROLE_MAPPING_ROWS)
