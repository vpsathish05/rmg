"""Migration: create role_recommendations pre-compute cache table."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS role_recommendations (
    pipeline_role_id  INTEGER PRIMARY KEY REFERENCES pipeline_requests(id) ON DELETE CASCADE,
    coe               TEXT,
    available         JSONB NOT NULL DEFAULT '[]',
    best_match        JSONB NOT NULL DEFAULT '[]',
    no_resource       BOOLEAN NOT NULL DEFAULT false,
    hire_signal       TEXT,
    kb_active         BOOLEAN NOT NULL DEFAULT false,
    total_evaluated   INTEGER NOT NULL DEFAULT 0,
    computed_at       TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'pending'
);
""")

conn.commit()
conn.close()
print("role_recommendations table created (or already exists).")
