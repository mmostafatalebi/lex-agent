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
- 15 tests, mypy strict, ruff clean.

## Architecture

Documented as pieces settle.
