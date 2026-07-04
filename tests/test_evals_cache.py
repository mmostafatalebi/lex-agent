from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from evals.cache import CacheError, CacheStats, _cache_key, cached_complete_json
from lexagent.config import settings
from tests.conftest import make_usage


class _Out(BaseModel):
    value: str


def _fake_bedrock(mocker: MockerFixture, value: str = "hello") -> Any:
    client = mocker.MagicMock()
    client.complete_json.return_value = (_Out(value=value), make_usage())
    return client


def test_record_mode_calls_bedrock_and_writes(mocker: MockerFixture, tmp_path: Path) -> None:
    client = _fake_bedrock(mocker)
    result, _ = cached_complete_json(client, "prompt", _Out, cache_dir=tmp_path, mode="record")
    assert result.value == "hello"
    assert client.complete_json.call_count == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_replay_mode_returns_cached_without_calling(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    recorder = _fake_bedrock(mocker, value="cached")
    cached_complete_json(recorder, "prompt", _Out, cache_dir=tmp_path, mode="record")

    replayer = _fake_bedrock(mocker, value="should-not-be-used")
    stats = CacheStats()
    result, _ = cached_complete_json(
        replayer, "prompt", _Out, cache_dir=tmp_path, mode="replay", stats=stats
    )
    assert result.value == "cached"
    assert replayer.complete_json.call_count == 0
    assert stats.hits == 1


def test_replay_mode_missing_raises_with_key(mocker: MockerFixture, tmp_path: Path) -> None:
    client = _fake_bedrock(mocker)
    key = _cache_key(settings.bedrock_model_id, None, "prompt", "_Out")
    with pytest.raises(CacheError, match=key):
        cached_complete_json(client, "prompt", _Out, cache_dir=tmp_path, mode="replay")


def test_auto_mode_uses_cache_when_present(mocker: MockerFixture, tmp_path: Path) -> None:
    client = _fake_bedrock(mocker, value="first")
    cached_complete_json(client, "prompt", _Out, cache_dir=tmp_path, mode="auto")
    assert client.complete_json.call_count == 1

    result, _ = cached_complete_json(client, "prompt", _Out, cache_dir=tmp_path, mode="auto")
    assert result.value == "first"
    assert client.complete_json.call_count == 1  # served from cache the second time


def test_cache_key_is_stable() -> None:
    a = _cache_key("model-x", "sys", "prompt", "Schema")
    b = _cache_key("model-x", "sys", "prompt", "Schema")
    c = _cache_key("model-x", None, "prompt", "Schema")
    assert a == b
    assert a != c
