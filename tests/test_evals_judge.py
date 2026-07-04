from typing import Any

from pytest_mock import MockerFixture

from evals import RISK_CATEGORIES
from evals.judge import CategoryDecision, MatchDecision, categorize_flag, judge_flag_match
from evals.models import ExpectedFlag
from lexagent.models import Flag, Severity
from tests.conftest import make_usage


def _flag() -> Flag:
    return Flag(
        id="flag_007_001",
        clause_id="clause_007",
        risk_description="Contractor bears unlimited liability with no cap.",
        severity=Severity.DEALBREAKER,
        verbatim_quote="unlimited liability for any and all damages",
        reasoning="No cap exposes the contractor to unbounded risk.",
    )


def _expected(category: str = "unlimited_liability") -> ExpectedFlag:
    return ExpectedFlag(
        clause_hint="Limitation of Liability",
        expected_severity=Severity.DEALBREAKER,
        risk_category=category,
        verbatim_hint="unlimited",
    )


def test_judge_returns_match_when_same_risk(mocker: MockerFixture) -> None:
    mocker.patch(
        "evals.judge.cached_complete_json",
        return_value=(
            MatchDecision(
                is_match=True,
                reasoning="Both describe uncapped contractor liability.",
                inferred_risk_category="unlimited_liability",
            ),
            make_usage(),
        ),
    )
    bedrock: Any = mocker.MagicMock()
    decision = judge_flag_match(bedrock, _flag(), _expected(), "clause text", mode="replay")
    assert decision.is_match is True


def test_judge_returns_no_match_when_categories_differ(mocker: MockerFixture) -> None:
    mocker.patch(
        "evals.judge.cached_complete_json",
        return_value=(
            MatchDecision(
                is_match=False,
                reasoning="Different underlying risks.",
                inferred_risk_category="broad_ip_assignment",
            ),
            make_usage(),
        ),
    )
    bedrock: Any = mocker.MagicMock()
    decision = judge_flag_match(
        bedrock, _flag(), _expected("overbroad_non_compete"), "clause text", mode="replay"
    )
    assert decision.is_match is False


def test_categorize_returns_vocabulary_value(mocker: MockerFixture) -> None:
    mocker.patch(
        "evals.judge.cached_complete_json",
        return_value=(CategoryDecision(category="unlimited_liability"), make_usage()),
    )
    bedrock: Any = mocker.MagicMock()
    category = categorize_flag(bedrock, _flag(), "clause text", mode="replay")
    assert category in RISK_CATEGORIES
    assert category == "unlimited_liability"


def test_categorize_falls_back_to_other_for_unknown(mocker: MockerFixture) -> None:
    mocker.patch(
        "evals.judge.cached_complete_json",
        return_value=(CategoryDecision(category="not_a_real_category"), make_usage()),
    )
    bedrock: Any = mocker.MagicMock()
    category = categorize_flag(bedrock, _flag(), "clause text", mode="replay")
    assert category == "other"
