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

-- IVFFlat index for ANN cosine similarity search
-- lists = sqrt(N) is ideal; 20 suits ~200-400 employees
-- Used by compute_semantic_skill_scores_ann() for ORDER BY <=> LIMIT K queries
DROP INDEX IF EXISTS idx_emp_skill_embed;
CREATE INDEX IF NOT EXISTS idx_emp_skill_embed_cosine
    ON employee_skill_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 20);
""")
print("employee_skill_embeddings table created!")
conn.close()
