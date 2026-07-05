"""Checkpointer factory for the analysis graph.

The graph pauses at human review and persists its state so a session can resume
after the process exits. Two backends are supported, selected by
``settings.checkpoint_backend``:

- ``sqlite``: a local file, good for development and the CLI.
- ``postgres``: the same database that holds the taxonomy, used in the deployed
  service so checkpoints survive across stateless invocations.

Both savers are built from a connection we own directly (rather than the
context-manager factories) so the checkpointer can outlive a single ``with``
block and back a long-running session.
"""

import sqlite3
from pathlib import Path

import psycopg
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg.rows import dict_row

from lexagent.config import settings


def get_checkpointer(path: str | None = None) -> BaseCheckpointSaver[str]:
    """Return a checkpointer for the configured backend.

    ``postgres`` uses ``settings.database_url``; ``sqlite`` uses ``path`` or
    ``settings.checkpoint_path``. An explicit ``path`` forces the SQLite backend.
    """
    if path is None and settings.checkpoint_backend == "postgres":
        return _postgres_checkpointer()
    return _sqlite_checkpointer(path)


def _postgres_checkpointer() -> PostgresSaver:
    if not settings.database_url:
        raise RuntimeError("database_url must be set when checkpoint_backend='postgres'")
    connection = psycopg.connect(
        settings.database_url, autocommit=True, row_factory=dict_row
    )
    saver = PostgresSaver(connection)
    saver.setup()
    return saver


def _sqlite_checkpointer(path: str | None) -> SqliteSaver:
    target = Path(path or settings.checkpoint_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target), check_same_thread=False)
    saver = SqliteSaver(connection)
    saver.setup()
    return saver
