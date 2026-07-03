from types import SimpleNamespace
from typing import Any

from pytest_mock import MockerFixture

from lexagent.models import ClauseType
from lexagent.retrieve import RetrievedExample, retrieve_similar


def _row(clause_type: str, similarity: float, is_risky: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        clause_type=clause_type,
        text=f"example clause for {clause_type}",
        is_risky=is_risky,
        notes="note",
        similarity=similarity,
    )


def _patch(mocker: MockerFixture, rows: list[SimpleNamespace]) -> Any:
    mocker.patch("lexagent.retrieve.EmbeddingsClient").return_value.embed.return_value = [
        0.1
    ] * 1024
    session = mocker.MagicMock()
    session.execute.return_value.all.return_value = rows
    scope = mocker.patch("lexagent.retrieve.session_scope")
    scope.return_value.__enter__.return_value = session
    return session


def test_returns_results_sorted_by_descending_similarity(mocker: MockerFixture) -> None:
    rows = [
        _row("liability", 0.91, is_risky=True),
        _row("liability", 0.74),
        _row("liability", 0.52),
    ]
    _patch(mocker, rows)
    results = retrieve_similar("uncapped liability clause", k=3)
    assert len(results) == 3
    assert all(isinstance(r, RetrievedExample) for r in results)
    similarities = [r.similarity for r in results]
    assert similarities == sorted(similarities, reverse=True)


def test_clause_type_filter_restricts_and_passes_param(mocker: MockerFixture) -> None:
    rows = [_row("ip_assignment", 0.88, is_risky=True), _row("ip_assignment", 0.61)]
    session = _patch(mocker, rows)
    results = retrieve_similar("assigns all IP", k=3, clause_type=ClauseType.IP_ASSIGNMENT)

    assert all(r.clause_type == ClauseType.IP_ASSIGNMENT for r in results)
    statement, params = session.execute.call_args.args
    assert "WHERE clause_type" in str(statement)
    assert params["clause_type"] == "ip_assignment"


def test_similarity_values_within_unit_interval(mocker: MockerFixture) -> None:
    rows = [_row("termination", 0.99), _row("termination", 0.50), _row("termination", 0.01)]
    _patch(mocker, rows)
    results = retrieve_similar("client may terminate at will", k=3)
    assert all(0.0 <= r.similarity <= 1.0 for r in results)
