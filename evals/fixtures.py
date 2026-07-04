"""Load hand-labelled fixture cases from ``evals/fixtures/``."""

from pathlib import Path

import yaml

from evals.models import FixtureCase

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixtures(names: list[str] | None = None) -> list[FixtureCase]:
    """Return every fixture case, or the subset named in ``names``."""
    cases: list[FixtureCase] = []
    for directory in sorted(FIXTURES_DIR.iterdir()):
        expected = directory / "expected.yaml"
        if not directory.is_dir() or not expected.exists():
            continue
        data = yaml.safe_load(expected.read_text(encoding="utf-8"))
        case = FixtureCase.model_validate(data)
        if names is None or case.name in names:
            cases.append(case)
    return cases
