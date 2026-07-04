import unicodedata

import pytest

from evals import RISK_CATEGORIES
from evals.fixtures import load_fixtures
from evals.models import FixtureCase
from lexagent.parse import parse_pdf


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def test_load_fixtures_returns_three_cases() -> None:
    cases = load_fixtures()
    assert len(cases) == 3
    assert all(isinstance(case, FixtureCase) for case in cases)
    assert {case.name for case in cases} == {
        "msa_problematic",
        "nda_broad_scope",
        "sow_ambiguous",
    }


def test_every_fixture_has_a_pdf() -> None:
    for case in load_fixtures():
        if not case.contract_path.exists():
            pytest.skip("fixture pdfs not generated; run scripts/build_fixtures.py")
        assert case.contract_path.suffix == ".pdf"


def test_risk_categories_are_in_vocabulary() -> None:
    for case in load_fixtures():
        for flag in case.expected_flags:
            assert flag.risk_category in RISK_CATEGORIES


def test_verbatim_hints_are_substrings_of_their_clause() -> None:
    for case in load_fixtures():
        if not case.contract_path.exists():
            pytest.skip("fixture pdfs not generated; run scripts/build_fixtures.py")
        contract = parse_pdf(case.contract_path)
        for flag in case.expected_flags:
            clause = None
            for candidate in contract.clauses:
                haystack = " ".join(
                    filter(None, [candidate.heading, candidate.section_number, candidate.text])
                )
                if _norm(flag.clause_hint) in _norm(haystack):
                    clause = candidate
                    break
            assert clause is not None, f"no clause for hint {flag.clause_hint!r} in {case.name}"
            assert _norm(flag.verbatim_hint) in _norm(clause.text), (
                f"{flag.verbatim_hint!r} not in clause {clause.id} of {case.name}"
            )
