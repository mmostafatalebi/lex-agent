"""Linear LangGraph state machine for contract analysis.

The graph threads a contract from raw file bytes to a ranked list of typed flags:
ingest, classify the document, classify clauses, analyze substantive clauses, and
rank. Each node is wrapped so that a failure short-circuits the run (status set to
``failed``) rather than partially proceeding.
"""

import logging
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any, Protocol

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from lexagent.bedrock import BedrockClient
from lexagent.models import GraphState
from lexagent.nodes.analyze_clause import analyze_clause
from lexagent.nodes.classify_clauses import classify_clauses
from lexagent.nodes.classify_document import classify_document
from lexagent.nodes.ingest import IngestError, ingest
from lexagent.nodes.rank import rank

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


def build_graph(bedrock: BedrockClient) -> CompiledStateGraph[GraphState]:
    """Build the analysis graph. The bedrock client is bound at build time."""
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

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "classify_document")
    graph.add_edge("classify_document", "classify_clauses")
    graph.add_edge("classify_clauses", "analyze_clauses")
    graph.add_edge("analyze_clauses", "rank")
    graph.add_edge("rank", END)

    return graph.compile()


def run_analysis(path: Path, bedrock: BedrockClient | None = None) -> GraphState:
    """Run the full analysis for a contract at ``path`` and return the final state."""
    client = bedrock if bedrock is not None else BedrockClient()
    compiled = build_graph(client)
    result = compiled.invoke(
        GraphState(),
        config={"configurable": {"source_path": str(path)}},
    )
    if isinstance(result, GraphState):
        return result
    return GraphState.model_validate(result)
