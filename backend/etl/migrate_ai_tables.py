"""Create AI-related tables for semantic skill matching."""
import psycopg2

conn = psycopg2.connect(
    host='rg-tenaliaiaz-prod-uksouth-02.postgres.database.azure.com',
    port=5432, dbname='postgres', user='adminuser',
    password='SKGvpsr05', sslmode='require'
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS employee_skill_embeddings (
    employee_id VARCHAR PRIMARY KEY REFERENCES employees(employee_id),
    skill_text  TEXT NOT NULL,
    embedding   vector(1536) NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_emp_skill_embed
    ON employee_skill_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);
""")
print("employee_skill_embeddings table created!")
conn.close()
