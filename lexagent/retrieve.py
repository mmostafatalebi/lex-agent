"""Cosine-similarity retrieval over the clause-examples taxonomy.

Embeds a query clause with Titan, then finds the nearest taxonomy examples in
pgvector using the ``<=>`` cosine-distance operator. Distance is converted to a
similarity in ``[0, 1]`` as ``1 - distance``.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy import text

from lexagent.db import session_scope
from lexagent.embeddings import EmbeddingsClient
from lexagent.models import ClauseType


class RetrievedExample(BaseModel):
    clause_type: ClauseType
    text: str
    is_risky: bool
    notes: str
    similarity: float  # cosine similarity in [0, 1]


def _to_vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


def _embed_query(clause_text: str) -> list[float]:
    return EmbeddingsClient().embed(clause_text)


def retrieve_similar(
    clause_text: str,
    k: int = 3,
    clause_type: ClauseType | None = None,
) -> list[RetrievedExample]:
    """Return the k most similar taxonomy examples to ``clause_text``.

    If ``clause_type`` is provided, restrict the search to that type.
    Uses cosine distance via pgvector.
    """
    vector_literal = _to_vector_literal(_embed_query(clause_text))

    where_sql = ""
    params: dict[str, Any] = {"query": vector_literal, "k": k}
    if clause_type is not None:
        where_sql = "WHERE clause_type = :clause_type"
        params["clause_type"] = clause_type.value

    statement = text(
        "SELECT clause_type, text, is_risky, notes, "
        "1 - (embedding <=> (:query)::vector) AS similarity "
        "FROM clause_examples "
        f"{where_sql} "
        "ORDER BY embedding <=> (:query)::vector "
        "LIMIT :k"
    )

    with session_scope() as session:
        rows = session.execute(statement, params).all()

    return [
        RetrievedExample(
            clause_type=ClauseType(row.clause_type),
            text=row.text,
            is_risky=row.is_risky,
            notes=row.notes,
            similarity=float(row.similarity),
        )
        for row in rows
    ]
