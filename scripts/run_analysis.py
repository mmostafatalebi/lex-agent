"""Run the contract analysis pipeline and print a structured summary.

Usage::

    uv run python scripts/run_analysis.py <path-to-contract>

Requires AWS credentials (AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
and DATABASE_URL in the environment (or a local .env).
"""

import sys
import time
from collections import Counter
from pathlib import Path

from lexagent.config import settings
from lexagent.graph import run_analysis
from lexagent.models import Clause, ClauseType


def _check_environment() -> list[str]:
    missing = []
    if not settings.aws_region:
        missing.append("AWS_REGION")
    if not settings.aws_access_key_id:
        missing.append("AWS_ACCESS_KEY_ID")
    if not settings.aws_secret_access_key:
        missing.append("AWS_SECRET_ACCESS_KEY")
    if not settings.database_url:
        missing.append("DATABASE_URL")
    return missing


def _heading_for(clauses: list[Clause], clause_id: str) -> str:
    for clause in clauses:
        if clause.id == clause_id:
            return clause.heading or clause.section_number or clause_id
    return clause_id


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: run_analysis.py <path-to-contract>", file=sys.stderr)
        return 2

    missing = _check_environment()
    if missing:
        print(
            "Missing required environment variables: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    path = Path(argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    print(f"Loading contract: {path}")
    started = time.perf_counter()
    state = run_analysis(path)
    elapsed = time.perf_counter() - started

    if state.status == "failed" or state.contract is None:
        print(f"Analysis failed: {state.error or 'unknown error'}", file=sys.stderr)
        return 1

    contract = state.contract
    print(f"Parsed {len(contract.clauses)} clauses ({len(contract.raw_text)} chars raw).")
    print(f"Document type: {contract.document_type.value}")

    substantive = [
        c for c in contract.clauses if c.clause_type and c.clause_type is not ClauseType.OTHER
    ]
    counts = Counter(c.clause_type.value for c in substantive if c.clause_type)
    summary = ", ".join(f"{name}={n}" for name, n in sorted(counts.items()))
    print(f"Classified clauses: {summary}")
    print(f"Analyzing {len(substantive)} substantive clauses...")
    print()
    print(f"Found {len(state.flags)} flags.")
    print()

    for index, flag in enumerate(state.flags, start=1):
        heading = _heading_for(contract.clauses, flag.clause_id)
        print(f"[{index}] {flag.severity.value.upper()} — {flag.clause_id} ({heading})")
        print(f"    {flag.risk_description}")
        quote = flag.verbatim_quote.strip().replace("\n", " ")
        print(f"    Quote: {quote[:120]}")
        print(f"    Reasoning: {flag.reasoning[:200]}")
        print()

    print(
        f"Analysis complete in {elapsed:.1f}s. "
        f"Estimated cost: ${state.total_cost_usd:.4f}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
