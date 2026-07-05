import pytest
from pytest_mock import MockerFixture

from lexagent.api.auth import check_api_key
from lexagent.api.errors import UnauthorizedError


def test_noop_when_not_required(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.api.auth.settings.require_api_key", False)
    check_api_key({})  # no exception


def test_missing_header_raises_when_required(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.api.auth.settings.require_api_key", True)
    mocker.patch("lexagent.api.auth.settings.api_key", "secret")
    with pytest.raises(UnauthorizedError):
        check_api_key({})


def test_wrong_key_raises_when_required(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.api.auth.settings.require_api_key", True)
    mocker.patch("lexagent.api.auth.settings.api_key", "secret")
    with pytest.raises(UnauthorizedError):
        check_api_key({"x-api-key": "wrong"})


def test_correct_key_passes_when_required(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.api.auth.settings.require_api_key", True)
    mocker.patch("lexagent.api.auth.settings.api_key", "secret")
    check_api_key({"X-Api-Key": "secret"})  # case-insensitive header, no exception
