"""initial: clause examples table

Revision ID: 0001_clause_examples
Revises:
Create Date: 2026-07-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_clause_examples"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "clause_examples",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("clause_type", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.Text(), nullable=False),
        sa.Column("is_risky", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("clause_type", "text_hash", name="uq_clause_examples_type_hash"),
    )

    op.create_index("ix_clause_examples_clause_type", "clause_examples", ["clause_type"])
    op.create_index(
        "ix_clause_examples_embedding",
        "clause_examples",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_with={"lists": 100},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_clause_examples_embedding", table_name="clause_examples")
    op.drop_index("ix_clause_examples_clause_type", table_name="clause_examples")
    op.drop_table("clause_examples")
