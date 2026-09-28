"""RunSqlTool / SqliteRunner must return data for every row-returning query, not only ones starting with SELECT."""

import sqlite3
from unittest.mock import AsyncMock

import pytest

from vanna.capabilities.sql_runner import RunSqlToolArgs
from vanna.core.tool import ToolContext
from vanna.core.user import User
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools.run_sql import RunSqlTool
from vanna.utils.sql_safety import sql_returns_rows


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "t.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE t (n INTEGER)")
        conn.execute("INSERT INTO t VALUES (1), (2)")
    return str(path)


def _context():
    return ToolContext(
        user=User(id="u", email="u@example.com", group_memberships=[]),
        conversation_id="c",
        request_id="r",
        agent_memory=DemoAgentMemory(),
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT n FROM t",
        "WITH x AS (SELECT n FROM t) SELECT n FROM x",
        "-- total rows\nSELECT n FROM t",
        "/* comment */ select n from t",
    ],
)
async def test_row_returning_queries_return_data(db, sql):
    tool = RunSqlTool(
        sql_runner=SqliteRunner(database_path=db), file_system=AsyncMock()
    )

    result = await tool.execute(_context(), RunSqlToolArgs(sql=sql))

    assert result.success
    assert result.metadata["row_count"] == 2
    assert "row(s) affected" not in result.result_for_llm


async def test_write_reports_real_rows_affected(db):
    tool = RunSqlTool(
        sql_runner=SqliteRunner(database_path=db),
        file_system=AsyncMock(),
        allow_write_sql=True,
    )

    result = await tool.execute(
        _context(), RunSqlToolArgs(sql="UPDATE t SET n = n + 1")
    )

    assert result.metadata["rows_affected"] == 2
    assert "2 row(s) affected" in result.result_for_llm


@pytest.mark.parametrize(
    "sql, expected",
    [
        ("SELECT 1", True),
        ("WITH x AS (SELECT 1) SELECT * FROM x", True),
        ("-- c\nSELECT 1", True),
        ("SHOW TABLES", True),
        ("DESCRIBE t", True),
        ("INSERT INTO t VALUES (1)", False),
        ("UPDATE t SET n = 1", False),
        ("", False),
    ],
)
def test_sql_returns_rows(sql, expected):
    assert sql_returns_rows(sql) is expected


class _FakeCursor:
    def __init__(self, description, rows, rowcount):
        self.description, self._rows, self.rowcount = description, rows, rowcount

    def execute(self, sql):
        pass

    def fetchall(self):
        return self._rows

    def close(self):
        pass


def _fake_postgres(cursor):
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from vanna.integrations.postgres.sql_runner import PostgresRunner

    runner = object.__new__(
        PostgresRunner
    )  # skip __init__: psycopg2 isn't installed in CI
    conn = MagicMock()
    conn.cursor.return_value = cursor
    runner.psycopg2 = SimpleNamespace(connect=lambda *a, **k: conn, extras=MagicMock())
    runner.connection_string = "postgresql://fake"
    return runner, conn


async def test_postgres_runner_returns_rows_for_cte():
    cursor = _FakeCursor(description=[("n",)], rows=[{"n": 1}, {"n": 2}], rowcount=2)
    runner, conn = _fake_postgres(cursor)

    df = await runner.run_sql(
        RunSqlToolArgs(sql="WITH x AS (SELECT 1 AS n) SELECT n FROM x"), _context()
    )

    assert list(df["n"]) == [1, 2]
    conn.commit.assert_not_called()


async def test_postgres_runner_reports_rows_affected_for_writes():
    cursor = _FakeCursor(description=None, rows=[], rowcount=3)
    runner, conn = _fake_postgres(cursor)

    df = await runner.run_sql(RunSqlToolArgs(sql="UPDATE t SET n = 1"), _context())

    assert df["rows_affected"].iloc[0] == 3
    conn.commit.assert_called_once()
