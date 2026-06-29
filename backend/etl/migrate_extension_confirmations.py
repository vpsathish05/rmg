"""
Migration: Create extension_confirmations table.

Tracks proactive extension confirmation emails sent to EMs before project end.
Stores response (no_extension / extend / partial) and which employees stay.

Usage:
    cd backend && source .venv/bin/activate
    python -m etl.migrate_extension_confirmations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from sqlalchemy import text


def migrate():
    db = SessionLocal()
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS extension_confirmations (
                id SERIAL PRIMARY KEY,
                project_id VARCHAR NOT NULL,
                client_id VARCHAR,
                project_end_date DATE,
                headcount INT,
                team_summary TEXT,
                -- Email tracking
                recipients TEXT[],
                first_sent_at TIMESTAMP,
                last_sent_at TIMESTAMP,
                send_count INT DEFAULT 0,
                -- Response
                response VARCHAR,
                responded_at TIMESTAMP,
                responded_by VARCHAR,
                -- For partial: which employees are staying
                staying_employee_ids TEXT[],
                new_end_date DATE,
                notes TEXT,
                -- Token for email callback (one-click response)
                token VARCHAR UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_ext_conf_project ON extension_confirmations(project_id);
            CREATE INDEX IF NOT EXISTS idx_ext_conf_token ON extension_confirmations(token);
            CREATE INDEX IF NOT EXISTS idx_ext_conf_response ON extension_confirmations(response);
        """))
        db.commit()
        print("✓ extension_confirmations table created successfully.")
    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
