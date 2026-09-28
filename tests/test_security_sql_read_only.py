"""Regression tests for executing LLM-generated SQL without filtering (vanna-ai/vanna#1078)."""

import sqlite3
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from vanna.capabilities.sql_runner import RunSqlToolArgs
from vanna.core.tool import ToolContext
from vanna.core.user import User
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.legacy.base import VannaBase
from vanna.tools.run_sql import RunSqlTool
from vanna.utils.sql_safety import UnsafeSqlError, ensure_read_only_sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM t",
        "  select name, sales from t order by sales desc limit 5;  ",
        "WITH top AS (SELECT * FROM t) SELECT name FROM top",
        "SELECT * FROM t WHERE x IN (SELECT id FROM u)",
        "-- comment\nSELECT 1",
        "SELECT * FROM t WHERE note = 'DROP TABLE t; DELETE FROM t'",  # keywords inside a string are data
        "SELECT create_date, updated_at, deleted FROM t",  # column names that look like keywords
        "SELECT replace(name, 'a', 'b') FROM t",
        "SHOW TABLES",
        "DESCRIBE t",
    ],
)
def test_read_only_sql_is_allowed(sql):
    ensure_read_only_sql(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE t",
        "DELETE FROM t",
        "UPDATE t SET x = 1",
        "INSERT INTO t VALUES (1)",
        "CREATE TABLE x (a int)",
        "SELECT 1; DROP TABLE t",  # stacked queries
        "WITH d AS (DELETE FROM t RETURNING *) SELECT * FROM d",  # write hidden in a CTE
        "BEGIN DBMS_SCHEDULER.create_job(job_name => 'x', job_type => 'EXECUTABLE'); END;",  # #1078 PoC style
        "SELECT DBMS_XMLGEN.getxml('select 1') FROM dual",
        "SELECT * INTO new_t FROM t",
        "SELECT 1 INTO OUTFILE '/tmp/x'",
        "SELECT load_extension('/tmp/evil.so')",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT * FROM read_csv('/etc/passwd')",
        "ATTACH DATABASE '/tmp/x.db' AS x",
        "PRAGMA writable_schema = 1",
        "",
    ],
)
def test_unsafe_sql_is_blocked(sql):
    with pytest.raises(UnsafeSqlError):
        ensure_read_only_sql(sql)


# --- legacy VannaBase ---


class _LegacyVanna(VannaBase):
    """Minimal concrete VannaBase that 'generates' fixed SQL and runs it on SQLite."""

    def __init__(self, generated_sql, config=None):
        # Fill all abstract methods with no-ops
        for name in VannaBase.__abstractmethods__:
            setattr(self, name, lambda *a, **k: None)
        super().__init__(config=config)
        self.generated_sql = generated_sql
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("CREATE TABLE t (name TEXT)")
        self.conn.execute("INSERT INTO t VALUES ('a')")
        self.run_sql_is_set = True
        self.run_sql = lambda sql: (
            pd.read_sql_query(sql, self.conn)
            if sql.lstrip().upper().startswith("SELECT")
            else self.conn.execute(sql)
        )

    def generate_sql(self, question, **kwargs):
        return self.generated_sql


_LegacyVanna.__abstractmethods__ = frozenset()


def _table_exists(vn):
    return (
        vn.conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE name = 't'"
        ).fetchone()[0]
        == 1
    )


def test_legacy_ask_does_not_run_llm_drop_table():
    vn = _LegacyVanna("DROP TABLE t")

    vn.ask("delete everything", print_results=False, visualize=False, auto_train=False)

    assert _table_exists(vn)


def test_legacy_ask_runs_select():
    vn = _LegacyVanna("SELECT name FROM t")

    sql, df, _ = vn.ask(
        "names?", print_results=False, visualize=False, auto_train=False
    )

    assert list(df["name"]) == ["a"]


def test_legacy_allow_write_sql_opt_out():
    vn = _LegacyVanna("DROP TABLE t", config={"allow_write_sql": True})

    vn.ask("drop it", print_results=False, visualize=False, auto_train=False)

    assert not _table_exists(vn)


# --- v2 RunSqlTool ---


class _RecordingRunner:
    def __init__(self):
        self.executed = []

    async def run_sql(self, args, context):
        self.executed.append(args.sql)
        return pd.DataFrame({"n": [1]})


def _context():
    return ToolContext(
        user=User(id="u", email="u@example.com", group_memberships=[]),
        conversation_id="c",
        request_id="r",
        agent_memory=DemoAgentMemory(),
    )


async def test_run_sql_tool_blocks_writes_by_default():
    runner = _RecordingRunner()
    tool = RunSqlTool(sql_runner=runner, file_system=AsyncMock())

    result = await tool.execute(_context(), RunSqlToolArgs(sql="DROP TABLE t"))

    assert result.success is False
    assert runner.executed == []


async def test_run_sql_tool_allows_select():
    runner = _RecordingRunner()
    tool = RunSqlTool(sql_runner=runner, file_system=AsyncMock())

    result = await tool.execute(_context(), RunSqlToolArgs(sql="SELECT 1 AS n"))

    assert result.success is True
    assert runner.executed == ["SELECT 1 AS n"]


async def test_run_sql_tool_allow_write_sql_opt_out():
    runner = _RecordingRunner()
    tool = RunSqlTool(sql_runner=runner, file_system=AsyncMock(), allow_write_sql=True)

    await tool.execute(_context(), RunSqlToolArgs(sql="DELETE FROM t"))

    assert runner.executed == ["DELETE FROM t"]
