"""SHA256-keyed disk cache for LLM responses.

Keeps evaluation runs deterministic and cheap: identical prompts resolve to the
same cache file, so a replay run makes no Bedrock calls at all. The cache is
committed to git on purpose.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from lexagent.bedrock import BedrockClient, TokenUsage
from lexagent.config import settings
from lexagent.models import ClauseType
from lexagent.retrieve import RetrievedExample

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("evals/cache")

T = TypeVar("T", bound=BaseModel)


class CacheError(RuntimeError):
    """Raised when a cache entry is required but missing, or the mode is invalid."""


@dataclass
class CacheStats:
    """Running totals for a single eval run."""

    hits: int = 0
    live_calls: int = 0
    total_cost_usd: float = 0.0

    def record_hit(self) -> None:
        self.hits += 1

    def record_live(self, usage: TokenUsage) -> None:
        self.live_calls += 1
        self.total_cost_usd += usage.total_cost_usd


def resolve_mode(override: str | None = None) -> str:
    mode = override or settings.eval_mode
    if mode not in {"auto", "replay", "record", "live"}:
        raise CacheError(f"Unknown cache mode: {mode}")
    return mode


def _cache_key(model_id: str, system: str | None, prompt: str, schema_name: str) -> str:
    digest = hashlib.sha256()
    for part in (model_id, system or "", prompt, schema_name):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def _write_response(path: Path, schema_name: str, result: BaseModel, usage: TokenUsage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": schema_name,
        "data": result.model_dump(mode="json"),
        "usage": usage.model_dump(mode="json"),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_response(path: Path, schema: type[T]) -> tuple[T, TokenUsage]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = schema.model_validate(payload["data"])
    usage = TokenUsage.model_validate(payload["usage"])
    return result, usage


def cached_complete_json(
    bedrock: BedrockClient,
    prompt: str,
    schema: type[T],
    system: str | None = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    mode: str = "auto",
    stats: CacheStats | None = None,
) -> tuple[T, TokenUsage]:
    """Wrap ``bedrock.complete_json`` with a disk cache.

    - ``auto``: read from cache if present, otherwise call Bedrock and write.
    - ``replay``: read from cache, raise if missing.
    - ``record``: always call Bedrock and overwrite the cache.
    - ``live``: bypass the cache entirely.
    """
    mode = resolve_mode(mode)
    key = _cache_key(settings.bedrock_model_id, system, prompt, schema.__name__)
    path = cache_dir / f"{key}.json"

    if mode == "replay":
        if not path.exists():
            raise CacheError(
                f"Cache miss in replay mode for key {key} (schema={schema.__name__})"
            )
        result, usage = _read_response(path, schema)
        if stats is not None:
            stats.record_hit()
        return result, usage

    if mode == "auto" and path.exists():
        result, usage = _read_response(path, schema)
        if stats is not None:
            stats.record_hit()
        return result, usage

    result, usage = bedrock.complete_json(prompt, schema, system=system)
    if mode != "live":
        _write_response(path, schema.__name__, result, usage)
    if stats is not None:
        stats.record_live(usage)
    return result, usage


def _retrieve_key(clause_text: str, k: int, clause_type: ClauseType | None) -> str:
    digest = hashlib.sha256()
    ct = clause_type.value if clause_type is not None else "none"
    for part in ("retrieve", ct, str(k), clause_text):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


RetrieveFn = Callable[[str, int, ClauseType | None], list[RetrievedExample]]


def make_cached_retrieve(
    real_retrieve: RetrieveFn,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    mode: str = "auto",
) -> RetrieveFn:
    """Return a drop-in replacement for ``retrieve_similar`` backed by the cache."""
    mode = resolve_mode(mode)

    def cached_retrieve(
        clause_text: str, k: int = 3, clause_type: ClauseType | None = None
    ) -> list[RetrievedExample]:
        key = _retrieve_key(clause_text, k, clause_type)
        path = cache_dir / f"retrieve_{key}.json"

        if mode == "replay" or (mode == "auto" and path.exists()):
            if not path.exists():
                raise CacheError(f"Retrieval cache miss in replay mode for key {key}")
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [RetrievedExample.model_validate(item) for item in raw]

        examples = real_retrieve(clause_text, k, clause_type)
        if mode != "live":
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = [example.model_dump(mode="json") for example in examples]
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return list(examples)

    return cached_retrieve
