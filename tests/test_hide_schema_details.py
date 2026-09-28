"""Schema lookups must not be shown to business users (vanna-ai/vanna#1105)."""

import sqlite3

import pytest

from vanna import Agent, AgentConfig
from vanna.components import DataFrameComponent
from vanna.core.agent.config import UiFeature, UiFeatures
from vanna.core.llm import LlmService
from vanna.core.llm.models import LlmResponse
from vanna.core.registry import ToolRegistry
from vanna.core.tool.models import ToolCall
from vanna.core.user import RequestContext, User, UserResolver
from vanna.integrations.local import LocalFileSystem
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.sqlite import SqliteRunner
from vanna.tools.run_sql import RunSqlTool, is_schema_query

SCHEMA_SQL = "SELECT name, sql FROM sqlite_master WHERE type = 'table'"
ANSWER_SQL = "SELECT SUM(total) AS revenue FROM invoices"


@pytest.mark.parametrize(
    "sql",
    [
        SCHEMA_SQL,
        "SELECT * FROM information_schema.columns WHERE table_name = 'x'",
        "SELECT * FROM pragma_table_info('invoices')",
        "SHOW TABLES",
        "DESCRIBE invoices",
        "SELECT table_name FROM all_tables",
    ],
)
def test_detects_schema_queries(sql):
    assert is_schema_query(sql)


@pytest.mark.parametrize(
    "sql",
    [
        ANSWER_SQL,
        "SELECT show_name, description FROM tv_shows",
        "SELECT * FROM my_table_info_log",
    ],
)
def test_business_queries_are_not_schema_queries(sql):
    assert not is_schema_query(sql)


class ScriptedLlm(LlmService):
    """Looks up the schema, runs the answer query, then replies."""

    def __init__(self):
        self.calls = 0

    async def send_request(self, request):
        self.calls += 1
        if self.calls == 1:
            return LlmResponse(
                tool_calls=[
                    ToolCall(id="1", name="run_sql", arguments={"sql": SCHEMA_SQL})
                ]
            )
        if self.calls == 2:
            return LlmResponse(
                tool_calls=[
                    ToolCall(id="2", name="run_sql", arguments={"sql": ANSWER_SQL})
                ]
            )
        return LlmResponse(content="Revenue was 30.", finish_reason="stop")

    async def stream_request(self, request):
        raise NotImplementedError

    async def validate_tools(self, tools):
        return []


class FixedUser(UserResolver):
    def __init__(self, groups):
        self.groups = groups

    async def resolve_user(self, request_context):
        return User(id="u", email="u@example.com", group_memberships=self.groups)


def _tables_shown(tmp_path, groups, ui_features=None):
    db = tmp_path / "shop.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE invoices (id INTEGER, customer_ssn TEXT, total REAL)"
        )
        conn.execute(
            "INSERT INTO invoices VALUES (1, '123-45-6789', 10), (2, '987-65-4321', 20)"
        )

    tools = ToolRegistry()
    tools.register_local_tool(
        RunSqlTool(
            sql_runner=SqliteRunner(database_path=str(db)),
            file_system=LocalFileSystem(working_directory=str(tmp_path)),
        ),
        access_groups=["user", "admin"],
    )
    config = AgentConfig(stream_responses=False)
    if ui_features is not None:
        config.ui_features = ui_features
    agent = Agent(
        llm_service=ScriptedLlm(),
        tool_registry=tools,
        user_resolver=FixedUser(groups),
        agent_memory=DemoAgentMemory(),
        config=config,
    )

    async def run():
        shown = []
        async for component in agent.send_message(
            RequestContext(cookies={}, headers={}), "revenue?"
        ):
            if isinstance(component.rich_component, DataFrameComponent):
                shown.append(component.rich_component.columns)
        return shown

    return run


async def test_business_user_sees_answer_but_not_schema(tmp_path):
    shown = await _tables_shown(tmp_path, ["user"])()

    assert shown == [
        ["revenue"]
    ]  # no ["name", "sql"] table listing CREATE TABLE ... customer_ssn


async def test_admin_still_sees_schema_lookups(tmp_path):
    shown = await _tables_shown(tmp_path, ["admin"])()

    assert shown == [["name", "sql"], ["revenue"]]


async def test_schema_details_can_be_opened_to_everyone(tmp_path):
    features = UiFeatures()
    features.register_feature(UiFeature.UI_FEATURE_SHOW_SCHEMA_DETAILS, [])

    shown = await _tables_shown(tmp_path, ["user"], features)()

    assert shown == [["name", "sql"], ["revenue"]]


def test_old_custom_ui_feature_configs_get_schema_details_default():
    # A config written before this feature existed: must not hide schema details from admins
    features = UiFeatures(
        feature_group_access={UiFeature.UI_FEATURE_SHOW_TOOL_NAMES: []}
    )

    admin = User(id="a", email="a@example.com", group_memberships=["admin"])
    user = User(id="u", email="u@example.com", group_memberships=["user"])
    assert features.can_user_access_feature(
        UiFeature.UI_FEATURE_SHOW_SCHEMA_DETAILS, admin
    )
    assert not features.can_user_access_feature(
        UiFeature.UI_FEATURE_SHOW_SCHEMA_DETAILS, user
    )
