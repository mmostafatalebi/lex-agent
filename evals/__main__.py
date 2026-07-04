"""Evaluation CLI: ``python -m evals``.

Runs the analysis pipeline against the fixture set, scores every metric, and
writes a Markdown report. Use ``--mode replay`` to run entirely from the
committed cache with no Bedrock calls.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from evals.analysis_eval import run_fixture
from evals.cache import DEFAULT_CACHE_DIR, CacheError, CacheStats, resolve_mode
from evals.fixtures import load_fixtures
from evals.models import FixtureReport
from evals.report import render_report
from lexagent.bedrock import BedrockClient, TokenUsage

logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)

_DEFAULT_REPORT = Path("evals/reports/latest.md")

_T = TypeVar("_T", bound=BaseModel)


class _OfflineBedrock(BedrockClient):
    """Stand-in used in replay mode so no AWS region or credentials are required.

    Every response is expected to come from the cache; a call here means a miss.
    """

    def __init__(self) -> None:
        pass

    def complete_json(
        self,
        prompt: str,
        schema: type[_T],
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> tuple[_T, TokenUsage]:
        raise CacheError("Bedrock is unavailable in replay mode; the response was not cached")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the analysis pipeline.")
    parser.add_argument("--mode", choices=["auto", "replay", "record", "live"], default=None)
    parser.add_argument("--fixtures", default=None, help="Comma-separated fixture names")
    parser.add_argument("--report-path", default=str(_DEFAULT_REPORT))
    parser.add_argument("--min-f1", type=float, default=0.0, help="Fail if any F1 is below this")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    return parser.parse_args(argv)


def main(argv: list[str], bedrock: BedrockClient | None = None) -> int:
    args = _parse_args(argv)
    mode = resolve_mode(args.mode)
    cache_dir = Path(args.cache_dir)
    names = args.fixtures.split(",") if args.fixtures else None

    cases = load_fixtures(names)
    if not cases:
        print("No fixtures found.", file=sys.stderr)
        return 1

    if bedrock is not None:
        client: BedrockClient = bedrock
    elif mode == "replay":
        client = _OfflineBedrock()
    else:
        client = BedrockClient()
    stats = CacheStats()
    reports: list[FixtureReport] = []

    for case in cases:
        print(f"Evaluating {case.name} (mode={mode})...")
        report = run_fixture(case, client, mode=mode, cache_dir=cache_dir, stats=stats)
        a = report.analysis
        print(
            f"  precision={a.precision:.2f} recall={a.recall:.2f} f1={a.f1:.2f} "
            f"hallucination={a.hallucination_rate:.2f} doc_type_ok={a.document_type_correct}"
        )
        reports.append(report)

    markdown = render_report(reports, cache_mode=mode, stats=stats)
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown, encoding="utf-8")
    print(f"Wrote report to {report_path}")

    below = [r.analysis.fixture_name for r in reports if r.analysis.f1 < args.min_f1]
    if below:
        print(f"F1 below {args.min_f1} for: {', '.join(below)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
