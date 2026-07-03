"""LangGraph state machine for contract analysis and human-reviewed redlining.

The graph threads a contract from raw file bytes to a ranked list of typed flags,
pauses at human review via ``interrupt()``, and on resume drafts and validates a
redline for every accepted flag. Analysis nodes are wrapped so a failure
short-circuits the run (status set to ``failed``) rather than partially proceeding;
the review node is left unwrapped so its ``GraphInterrupt`` can propagate.
"""

import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any, Protocol

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from lexagent.bedrock import BedrockClient
from lexagent.checkpoint import get_checkpointer
from lexagent.models import Flag, GraphState, HumanDecision
from lexagent.nodes.analyze_clause import analyze_clause
from lexagent.nodes.classify_clauses import classify_clauses
from lexagent.nodes.classify_document import classify_document
from lexagent.nodes.draft_redlines import draft_redlines
from lexagent.nodes.human_review import human_review
from lexagent.nodes.ingest import IngestError, ingest
from lexagent.nodes.rank import rank
from lexagent.nodes.validate_redlines import validate_redlines

logger = logging.getLogger(__name__)

_MUTABLE_FIELDS = (
    "contract",
    "flags",
    "human_decisions",
    "redlines",
    "status",
    "error",
    "total_cost_usd",
)


def _updates(state: GraphState) -> dict[str, Any]:
    return {field: getattr(state, field) for field in _MUTABLE_FIELDS}


class _ConfigNode(Protocol):
    """A node taking the state and run config, returning channel updates."""

    def __call__(self, state: GraphState, config: RunnableConfig) -> dict[str, Any]: ...


def _guarded(name: str, fn: Callable[[GraphState], GraphState]) -> _ConfigNode:
    """Wrap a node so exceptions mark the run failed and failed runs pass through."""

    def wrapper(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        if state.status == "failed":
            return {}
        try:
            new_state = fn(state)
        except Exception as exc:
            logger.exception("node %s failed", name)
            return {"status": "failed", "error": f"{name}: {exc}"}
        return _updates(new_state)

    return wrapper


def _plain(fn: Callable[[GraphState], GraphState]) -> _ConfigNode:
    """Wrap a node without catching exceptions, so a GraphInterrupt propagates."""

    def wrapper(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
        if state.status == "failed":
            return {}
        return _updates(fn(state))

    return wrapper


def _ingest_node(state: GraphState, config: RunnableConfig) -> dict[str, Any]:
    if state.status == "failed":
        return {}
    try:
        configurable = config.get("configurable") or {}
        source_path = configurable.get("source_path")
        if not source_path:
            raise IngestError("source_path missing from run configuration")
        new_state = ingest(state, Path(source_path))
    except Exception as exc:
        logger.exception("node ingest failed")
        return {"status": "failed", "error": f"ingest: {exc}"}
    return _updates(new_state)


def build_graph(
    bedrock: BedrockClient, checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[GraphState]:
    """Build the analysis graph. The bedrock client and checkpointer bind at build time."""
    graph = StateGraph(GraphState)
    graph.add_node("ingest", _ingest_node)
    graph.add_node(
        "classify_document",
        _guarded("classify_document", partial(classify_document, bedrock=bedrock)),
    )
    graph.add_node(
        "classify_clauses",
        _guarded("classify_clauses", partial(classify_clauses, bedrock=bedrock)),
    )
    graph.add_node(
        "analyze_clauses",
        _guarded("analyze_clauses", partial(analyze_clause, bedrock=bedrock)),
    )
    graph.add_node("rank", _guarded("rank", rank))
    graph.add_node("human_review", _plain(human_review))
    graph.add_node(
        "draft_redlines",
        _guarded("draft_redlines", partial(draft_redlines, bedrock=bedrock)),
    )
    graph.add_node("validate_redlines", _guarded("validate_redlines", validate_redlines))

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "classify_document")
    graph.add_edge("classify_document", "classify_clauses")
    graph.add_edge("classify_clauses", "analyze_clauses")
    graph.add_edge("analyze_clauses", "rank")
    graph.add_edge("rank", "human_review")
    graph.add_edge("human_review", "draft_redlines")
    graph.add_edge("draft_redlines", "validate_redlines")
    graph.add_edge("validate_redlines", END)

    return graph.compile(checkpointer=checkpointer)


def run_analysis(
    path: Path,
    thread_id: str,
    bedrock: BedrockClient | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> dict[str, Any]:
    """Run the analysis graph until an interrupt or completion.

    Returns the LangGraph output dict. If interrupted, the output contains
    ``__interrupt__`` with the review payload; if complete, it contains the
    final state values.
    """
    client = bedrock if bedrock is not None else BedrockClient()
    saver = checkpointer if checkpointer is not None else get_checkpointer()
    compiled = build_graph(client, saver)
    result = compiled.invoke(
        GraphState(thread_id=thread_id),
        config={"configurable": {"thread_id": thread_id, "source_path": str(path)}},
    )
    return dict(result)


def load_review_flags(
    thread_id: str,
    bedrock: BedrockClient | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> list[Flag]:
    """Return the flags of a paused session so a resuming caller can review them."""
    client = bedrock if bedrock is not None else BedrockClient()
    saver = checkpointer if checkpointer is not None else get_checkpointer()
    compiled = build_graph(client, saver)
    snapshot = compiled.get_state({"configurable": {"thread_id": thread_id}})
    values = snapshot.values
    flags = values.get("flags", []) if isinstance(values, dict) else getattr(values, "flags", [])
    return list(flags)


def resume_analysis(
    thread_id: str,
    decisions: list[HumanDecision],
    bedrock: BedrockClient | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> dict[str, Any]:
    """Resume a paused analysis with the human's decisions."""
    client = bedrock if bedrock is not None else BedrockClient()
    saver = checkpointer if checkpointer is not None else get_checkpointer()
    compiled = build_graph(client, saver)
    payload = [decision.model_dump() for decision in decisions]
    result = compiled.invoke(
        Command(resume=payload),
        config={"configurable": {"thread_id": thread_id}},
    )
    return dict(result)
