"""Create the Sentellent RAG, memory, and ingestion schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-30
"""

from alembic import op

from app.models import Base


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_document_chunk_embedding_hnsw "
        "ON document_chunk USING hnsw (embedding vector_cosine_ops)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_embedding_cache_embedding_hnsw "
        "ON embedding_cache USING hnsw (embedding vector_cosine_ops)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_document_chunk_text_fts "
        "ON document_chunk USING gin (to_tsvector('english', text))"
    )
    bind.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_ingestion_job_active_stock "
        "ON ingestion_job (stock_id) WHERE status IN ('queued', 'running')"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX IF EXISTS ix_document_chunk_text_fts")
    bind.exec_driver_sql("DROP INDEX IF EXISTS uq_ingestion_job_active_stock")
    bind.exec_driver_sql("DROP INDEX IF EXISTS ix_embedding_cache_embedding_hnsw")
    bind.exec_driver_sql("DROP INDEX IF EXISTS ix_document_chunk_embedding_hnsw")
    Base.metadata.drop_all(bind=bind)
