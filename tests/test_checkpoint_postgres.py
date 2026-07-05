from typing import Any

import pytest
from pytest_mock import MockerFixture

from lexagent import checkpoint


def test_postgres_backend_returns_postgres_saver(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.checkpoint.settings.checkpoint_backend", "postgres")
    mocker.patch("lexagent.checkpoint.settings.database_url", "postgresql://u:p@localhost/db")
    mocker.patch("lexagent.checkpoint.psycopg.connect", return_value=mocker.MagicMock())
    fake_saver = mocker.MagicMock()
    ctor = mocker.patch("lexagent.checkpoint.PostgresSaver", return_value=fake_saver)

    saver: Any = checkpoint.get_checkpointer()
    assert saver is fake_saver
    ctor.assert_called_once()
    fake_saver.setup.assert_called_once()


def test_postgres_backend_without_url_raises(mocker: MockerFixture) -> None:
    mocker.patch("lexagent.checkpoint.settings.checkpoint_backend", "postgres")
    mocker.patch("lexagent.checkpoint.settings.database_url", None)
    with pytest.raises(RuntimeError, match="database_url"):
        checkpoint.get_checkpointer()


def test_sqlite_backend_returns_sqlite_saver(mocker: MockerFixture, tmp_path: Any) -> None:
    from langgraph.checkpoint.sqlite import SqliteSaver

    mocker.patch("lexagent.checkpoint.settings.checkpoint_backend", "sqlite")
    saver = checkpoint.get_checkpointer(str(tmp_path / "cp.db"))
    assert isinstance(saver, SqliteSaver)
