import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver

from lexagent.graph import load_review_flags
from tests.conftest import make_analysis_dispatch

_SCRIPT = Path(__file__).parent.parent / "scripts" / "run_analysis.py"


def _load_cli() -> Any:
    spec = importlib.util.spec_from_file_location("run_analysis_cli", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cli(fake_bedrock_client: Any, mock_retrieve_similar: Any) -> Any:
    module = _load_cli()
    fake_bedrock_client.complete_json.side_effect = make_analysis_dispatch()
    return module


def _run(module: Any, argv: list[str], bedrock: Any, saver: Any) -> int:
    return int(module.main(argv, bedrock=bedrock, checkpointer=saver))


def test_decisions_file_mode(
    cli: Any, fake_bedrock_client: Any, tmp_path: Path, sample_msa_pdf: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    saver = MemorySaver()
    # A plain run with no decision source pauses; capture the thread id.
    code = _run(cli, [str(sample_msa_pdf)], fake_bedrock_client, saver)
    assert code == 0
    thread_id = re.search(r"Session: (\w+)", capsys.readouterr().out).group(1)  # type: ignore[union-attr]

    flags = load_review_flags(thread_id, bedrock=fake_bedrock_client, checkpointer=saver)
    decisions = [{"flag_id": flag.id, "decision": "accept"} for flag in flags]
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")

    # A fresh run with a decisions file drafts redlines in one shot.
    code = _run(
        cli, [str(sample_msa_pdf), "--decisions", str(decisions_path)], fake_bedrock_client, saver
    )
    printed = capsys.readouterr().out
    assert code == 0
    assert "REDLINES" in printed
    assert "[1]" in printed


def test_auto_accept_all_mode(
    cli: Any, fake_bedrock_client: Any, sample_msa_pdf: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    saver = MemorySaver()
    code = _run(cli, [str(sample_msa_pdf), "--auto-accept-all"], fake_bedrock_client, saver)
    printed = capsys.readouterr().out
    assert code == 0
    assert "REDLINES" in printed
    produced = re.search(r"produced (\d+) redline", printed)
    assert produced is not None and int(produced.group(1)) >= 5


def test_resume_mode(
    cli: Any, fake_bedrock_client: Any, sample_msa_pdf: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    saver = MemorySaver()
    # Fresh run pauses at review.
    _run(cli, [str(sample_msa_pdf)], fake_bedrock_client, saver)
    thread_id = re.search(r"Session: (\w+)", capsys.readouterr().out).group(1)  # type: ignore[union-attr]

    # Resume the paused session, accepting every flag.
    code = _run(cli, ["--resume", thread_id, "--auto-accept-all"], fake_bedrock_client, saver)
    printed = capsys.readouterr().out
    assert code == 0
    assert "REDLINES" in printed
    produced = re.search(r"produced (\d+) redline", printed)
    assert produced is not None and int(produced.group(1)) >= 5


def test_invalid_decisions_file_exits_nonzero(
    cli: Any, fake_bedrock_client: Any, tmp_path: Path, sample_msa_pdf: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"decision": "accept"}]), encoding="utf-8")  # missing flag_id
    saver = MemorySaver()
    code = _run(cli, [str(sample_msa_pdf), "--decisions", str(bad)], fake_bedrock_client, saver)
    err = capsys.readouterr().err
    assert code == 1
    assert "flag_id" in err or "Invalid decisions" in err
