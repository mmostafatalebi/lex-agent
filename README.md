# LexAgent

A contract review agent for freelancers and small businesses. Upload a contract, get a structured second opinion in five minutes, then review each flag before drafting redlines.

Under active development.

## Quick start

```bash
uv sync
uv run python scripts/build_fixtures.py
uv run pytest
```

## What is here today

- PDF and DOCX parsing that preserves character offsets, so any downstream analysis can cite verbatim source text.
- A typed data model (contracts, clauses, flags, redlines) built on Pydantic.
- A clause-boundary chunker with numbered-section detection and paragraph fallback.
- A sample Master Service Agreement fixture with realistic problematic clauses to analyse against.
- An AWS Bedrock client for Claude with typed structured output and retry backoff.
- Titan embeddings for representing clause text as 1024-dimensional vectors.
- PostgreSQL + pgvector storing a taxonomy of canonical and risky clause examples across nine clause types.
- A cosine-similarity retrieval helper that returns the most similar taxonomy examples for a given clause.
- A Docker Compose file for the local pgvector database.
- A LangGraph state machine that runs a contract from raw file bytes to a ranked list of typed flags.
- Per-clause risk analysis grounded in the taxonomy retrieval, with a verbatim-quote gate that drops flags whose supporting quote is not a literal substring of the source clause.
- 42 tests, mypy strict, ruff clean.

## Local database

```bash
docker compose up -d
uv run alembic upgrade head
uv run python scripts/seed_taxonomy.py  # requires AWS credentials
```

## Analyze a contract

```bash
# requires AWS credentials, local Postgres up with taxonomy seeded
uv run python scripts/run_analysis.py fixtures/sample_msa.pdf
```

## Architecture

Documented as pieces settle.
