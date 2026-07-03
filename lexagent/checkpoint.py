"""SQLite checkpointer factory for the analysis graph.

The graph pauses at human review and persists its state so a session can resume
after the process exits. ``SqliteSaver.from_conn_string`` is a context manager in
the installed version; here we own the connection directly so the checkpointer can
outlive a single ``with`` block and back a long-running interactive session.
"""

import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from lexagent.config import settings


def get_checkpointer(path: str | None = None) -> SqliteSaver:
    """Return a SqliteSaver rooted at ``path`` (defaults to settings.checkpoint_path).

    The parent directory is created if it does not exist.
    """
    target = Path(path or settings.checkpoint_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target), check_same_thread=False)
    saver = SqliteSaver(connection)
    saver.setup()
    return saver
