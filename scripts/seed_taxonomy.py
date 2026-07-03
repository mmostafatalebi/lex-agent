"""Populate the ``clause_examples`` table from the canonical taxonomy.

Idempotent: entries are keyed by ``(clause_type, text_hash)``, so re-running only
embeds and writes rows whose text is new or changed. Requires AWS credentials
(for Titan embeddings) and a reachable database.

Usage::

    uv run python scripts/seed_taxonomy.py
"""

from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from lexagent.db import ClauseExample, ensure_extension, get_engine, session_scope
from lexagent.embeddings import EmbeddingsClient
from lexagent.taxonomy import TAXONOMY

# Approximate Titan Text Embeddings V2 price for a rough cost estimate.
TITAN_COST_PER_MTOKEN_USD = 0.02


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _estimate_tokens(value: str) -> int:
    return max(1, len(value) // 4)


def main() -> None:
    engine = get_engine()
    ensure_extension(engine)
    client = EmbeddingsClient()

    inserted = 0
    updated = 0
    unchanged = 0
    calls = 0
    estimated_tokens = 0

    with session_scope() as session:
        existing: set[tuple[str, str]] = {
            (row.clause_type, row.text_hash)
            for row in session.execute(
                select(ClauseExample.clause_type, ClauseExample.text_hash)
            ).all()
        }

        for entry in TAXONOMY:
            text_hash = _text_hash(entry.text)
            key = (entry.clause_type.value, text_hash)
            if key in existing:
                unchanged += 1
                continue

            embedding = client.embed(entry.text)
            calls += 1
            estimated_tokens += _estimate_tokens(entry.text)

            statement = pg_insert(ClauseExample).values(
                clause_type=entry.clause_type.value,
                text=entry.text,
                text_hash=text_hash,
                is_risky=entry.is_risky,
                notes=entry.notes,
                embedding=embedding,
            )
            statement = statement.on_conflict_do_update(
                index_elements=["clause_type", "text_hash"],
                set_={
                    "text": entry.text,
                    "is_risky": entry.is_risky,
                    "notes": entry.notes,
                    "embedding": embedding,
                },
            )
            session.execute(statement)
            inserted += 1

    cost = estimated_tokens / 1_000_000 * TITAN_COST_PER_MTOKEN_USD
    print(f"{inserted} inserted, {updated} updated, {unchanged} unchanged, cost: ${cost:.4f}")
    print(f"Bedrock embedding calls: {calls}")


if __name__ == "__main__":
    main()
