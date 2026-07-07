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
- A LangGraph `interrupt()` pauses the analysis after ranking so a human can accept or reject each flag. State persists to a SQLite checkpointer, so a session can resume after a full process restart.
- A drafting node produces a `Redline` for every accepted flag, using the LLM to write a minimal-edit revised clause with a justification. Every redline is gated by a substring check against the source clause.
- An evaluation harness that runs the analysis pipeline against three hand-labelled contracts and produces a Markdown report with precision, recall, F1, hallucination rate, and retrieval quality metrics. See [evals/reports/latest.md](evals/reports/latest.md).
- Response caching that keeps the eval deterministic and cheap to re-run.
- An HTTP API that walks through the full contract-review flow (upload → analyze → review → decisions → redlines) over six REST endpoints, deployed to AWS Lambda behind API Gateway.
- Infrastructure as code in Python CDK: Aurora Serverless v2 Postgres (scales to zero), S3 for uploaded contracts, single Lambda serving all routes via `aws-lambda-powertools`.
- A Next.js 14 web app in `web/` that talks to the deployed API: drag-and-drop upload, flag review with accept/reject, redlines side by side. Deployable to Vercel or any Next.js-compatible host.
- 99 tests, mypy strict, ruff clean.

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

## Review a contract

```bash
# interactive
uv run python scripts/run_analysis.py fixtures/sample_msa.pdf

# resume a paused session
uv run python scripts/run_analysis.py --resume <thread_id>

# non-interactive with a decisions file
uv run python scripts/run_analysis.py fixtures/sample_msa.pdf \
  --decisions decisions.json --output redlines.md
```

## Evaluate the pipeline

```bash
# use the committed cache (deterministic, no AWS calls)
uv run python -m evals --mode replay

# rebuild the cache from real Bedrock (costs money, updates evals/cache/)
uv run python -m evals --mode record
```

The scored report lands at [evals/reports/latest.md](evals/reports/latest.md).

## Run the web app

```bash
cd web
cp .env.example .env.local
# edit NEXT_PUBLIC_API_URL to point at your backend, or set NEXT_PUBLIC_USE_MOCK=true
npm install
npm run dev
# open http://localhost:3000
```

Deploy the frontend to Vercel:

```bash
cd web
vercel deploy
# set NEXT_PUBLIC_API_URL in the Vercel dashboard to your deployed API Gateway URL
```

## Deploy to AWS

```bash
# One-time
uv sync --group infra
uv run cdk bootstrap  # per account/region

# Synthesize CloudFormation (no credentials needed)
uv run --group infra cdk synth --quiet

# Deploy (builds and pushes the container image, then updates the stack)
uv run cdk deploy

# The API URL and secret ARNs are in the CDK outputs.
export API_URL=https://xxx.execute-api.us-east-1.amazonaws.com
export API_KEY=your-key

# Upload a contract
curl -X POST "$API_URL/contracts" \
  -H "x-api-key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filename": "sample.pdf", "content_base64": "'"$(base64 -i fixtures/sample_msa.pdf)"'"}'
```

### Endpoints

- `POST /contracts` — upload a base64 PDF/DOCX, returns a content-addressed `contract_id`.
- `POST /analyses` — start analysis for a `contract_id`; runs until the human-review pause.
- `GET /analyses/{thread_id}` — current status and flags.
- `POST /analyses/{thread_id}/decisions` — submit accept/reject decisions; drafts redlines.
- `GET /analyses/{thread_id}/results` — final redlines once the analysis is complete.

### Cost profile

Aurora Serverless v2 scales to a minimum of 0 ACU and the Lambda cold path bills
only on use, so an idle stack costs roughly $0/day for compute (VPC interface
endpoints are the small standing cost). A warm analyzed contract is on the order
of $0.01 in Bedrock calls.

## Architecture

Documented as pieces settle.
