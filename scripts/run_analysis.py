"""Run the contract analysis pipeline with human review and redline drafting.

Modes::

    # interactive review
    uv run python scripts/run_analysis.py fixtures/sample_msa.pdf

    # non-interactive with a decisions file, redlines written to a file
    uv run python scripts/run_analysis.py fixtures/sample_msa.pdf \
        --decisions decisions.json --output redlines.md

    # accept or reject every flag without prompting
    uv run python scripts/run_analysis.py fixtures/sample_msa.pdf --auto-accept-all

    # resume a paused session (no PDF path required)
    uv run python scripts/run_analysis.py --resume <thread_id>

Requires AWS credentials and DATABASE_URL in the environment (or a local .env).
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lexagent.bedrock import BedrockClient
from lexagent.checkpoint import get_checkpointer
from lexagent.config import settings
from lexagent.graph import load_review_flags, resume_analysis, run_analysis
from lexagent.models import Clause, Flag, HumanDecision, Redline

# Quiet the checkpointer's per-type deserialization notices for clean output.
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)


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


def _print_flags(flags: list[Flag], clauses: list[Clause]) -> None:
    print(f"Found {len(flags)} flags.\n")
    for index, flag in enumerate(flags, start=1):
        heading = _heading_for(clauses, flag.clause_id)
        print(f"[{index}] {flag.severity.value.upper()} — {flag.clause_id} ({heading})")
        print(f'    "{flag.verbatim_quote.strip()[:100]}"')


def _load_decisions_file(path: Path) -> list[HumanDecision]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Decisions file must contain a JSON list")
    return [HumanDecision.model_validate(item) for item in raw]


def _prompt_decisions(flags: list[Flag], clauses: list[Clause]) -> list[HumanDecision]:
    decisions: list[HumanDecision] = []
    for index, flag in enumerate(flags, start=1):
        heading = _heading_for(clauses, flag.clause_id)
        print(f"\n[{index}] {flag.severity.value.upper()} — {flag.clause_id} ({heading})")
        print(f'    "{flag.verbatim_quote.strip()[:200]}"')
        answer = input(f"    Accept flag [{index}]? [y/N/skip]: ").strip().lower()
        if answer == "skip":
            continue
        decision = "accept" if answer in {"y", "yes"} else "reject"
        decisions.append(HumanDecision(flag_id=flag.id, decision=decision))
    return decisions


def _has_decision_source(args: argparse.Namespace) -> bool:
    return bool(args.decisions or args.auto_accept_all or args.auto_reject_all)


def _collect_decisions(
    flags: list[Flag], clauses: list[Clause], args: argparse.Namespace
) -> list[HumanDecision]:
    if args.decisions:
        return _load_decisions_file(Path(args.decisions))
    if args.auto_accept_all:
        return [HumanDecision(flag_id=flag.id, decision="accept") for flag in flags]
    if args.auto_reject_all:
        return [HumanDecision(flag_id=flag.id, decision="reject") for flag in flags]
    return _prompt_decisions(flags, clauses)


def _format_redlines_markdown(redlines: list[Redline], clauses: list[Clause]) -> str:
    lines = ["# Redlines", ""]
    if not redlines:
        lines.append("_No redlines were drafted._")
        return "\n".join(lines) + "\n"
    for index, redline in enumerate(redlines, start=1):
        heading = _heading_for(clauses, redline.clause_id)
        lines.append(f"## [{index}] {redline.clause_id} ({heading})")
        lines.append("")
        lines.append(f"**Original:** {redline.original_text}")
        lines.append("")
        lines.append(f"**Revised:** {redline.revised_text}")
        lines.append("")
        lines.append(f"**Justification:** {redline.justification}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _print_redlines(redlines: list[Redline], clauses: list[Clause]) -> None:
    print("\nREDLINES")
    print("========\n")
    if not redlines:
        print("No redlines were drafted.")
        return
    for index, redline in enumerate(redlines, start=1):
        heading = _heading_for(clauses, redline.clause_id)
        print(f"[{index}] {redline.clause_id} ({heading})")
        print(f'    Original: "{redline.original_text.strip()[:120]}"')
        print(f'    Revised:  "{redline.revised_text.strip()[:120]}"')
        print(f"    Justification: {redline.justification}")
        print()


def _finalize(final: dict[str, Any], args: argparse.Namespace, thread_id: str) -> int:
    contract = final.get("contract")
    clauses: list[Clause] = list(contract.clauses) if contract is not None else []
    redlines: list[Redline] = list(final.get("redlines", []))

    print(f"\nDrafting redlines produced {len(redlines)} redline(s).")
    _print_redlines(redlines, clauses)

    if args.output:
        Path(args.output).write_text(
            _format_redlines_markdown(redlines, clauses), encoding="utf-8"
        )
        print(f"Wrote redlines to {args.output}")

    print(f"Analysis complete. thread_id: {thread_id}")
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a contract and draft redlines.")
    parser.add_argument("path", nargs="?", help="Path to a PDF or DOCX contract")
    parser.add_argument("--resume", metavar="THREAD_ID", help="Resume a paused session")
    parser.add_argument("--decisions", metavar="FILE", help="JSON decisions file")
    parser.add_argument("--auto-accept-all", action="store_true", help="Accept every flag")
    parser.add_argument("--auto-reject-all", action="store_true", help="Reject every flag")
    parser.add_argument("--output", metavar="FILE", help="Write redlines to a Markdown file")
    return parser.parse_args(argv)


def main(
    argv: list[str],
    bedrock: BedrockClient | None = None,
    checkpointer: Any = None,
) -> int:
    args = _parse_args(argv)

    if bedrock is None:
        missing = _check_environment()
        if missing:
            print("Missing required environment variables: " + ", ".join(missing), file=sys.stderr)
            return 1

    saver = checkpointer if checkpointer is not None else get_checkpointer()

    try:
        if args.resume:
            return _run_resume(args, bedrock, saver)
        return _run_fresh(args, bedrock, saver)
    except ValidationError as exc:
        print(f"Invalid decisions payload: {exc}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _run_resume(args: argparse.Namespace, bedrock: BedrockClient | None, saver: Any) -> int:
    thread_id = args.resume
    flags = load_review_flags(thread_id, bedrock=bedrock, checkpointer=saver)
    if not flags:
        print(f"No paused session found for thread_id: {thread_id}", file=sys.stderr)
        return 1
    print(f"Resuming session: {thread_id}")
    _print_flags(flags, [])
    if not _has_decision_source(args) and not sys.stdin.isatty():
        print(
            "Provide --decisions, --auto-accept-all, or --auto-reject-all to resume.",
            file=sys.stderr,
        )
        return 1
    decisions = _collect_decisions(flags, [], args)
    final = resume_analysis(thread_id, decisions, bedrock=bedrock, checkpointer=saver)
    return _finalize(final, args, thread_id)


def _run_fresh(args: argparse.Namespace, bedrock: BedrockClient | None, saver: Any) -> int:
    if not args.path:
        print("A contract path is required unless --resume is given.", file=sys.stderr)
        return 2
    path = Path(args.path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    thread_id = uuid.uuid4().hex[:12]
    print(f"Session: {thread_id}")
    print(f"Analyzing {path}...")
    out = run_analysis(path, thread_id, bedrock=bedrock, checkpointer=saver)

    if "__interrupt__" not in out:
        print(f"Analysis did not reach review (status: {out.get('status')}).", file=sys.stderr)
        if out.get("error"):
            print(f"Error: {out['error']}", file=sys.stderr)
        return 1

    contract = out.get("contract")
    clauses: list[Clause] = list(contract.clauses) if contract is not None else []
    flags = list(out.get("flags", []))
    print()
    _print_flags(flags, clauses)

    # Without a decision source and no interactive terminal, leave the session
    # paused so a separate invocation can resume it with the printed thread_id.
    if not _has_decision_source(args) and not sys.stdin.isatty():
        print(f"\nSession paused. Resume with: --resume {thread_id}")
        return 0

    decisions = _collect_decisions(flags, clauses, args)
    accepted = sum(1 for d in decisions if d.decision == "accept")
    print(f"\nDrafting redlines for {accepted} accepted flag(s)...")
    final = resume_analysis(thread_id, decisions, bedrock=bedrock, checkpointer=saver)
    return _finalize(final, args, thread_id)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
