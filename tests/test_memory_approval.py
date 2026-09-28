"""Human approval before saving to tool memory (vanna-ai/vanna#1103)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from vanna.capabilities.agent_memory import AgentMemory
from vanna.components import ButtonComponent
from vanna.core.registry import ToolRegistry
from vanna.core.tool import ToolContext
from vanna.core.user import User
from vanna.core.workflow import DefaultWorkflowHandler
from vanna.tools.agent_memory import (
    SaveQuestionToolArgsParams,
    SaveQuestionToolArgsTool,
)

ARGS = SaveQuestionToolArgsParams(
    question="total sales?",
    tool_name="run_sql",
    args={"sql": "SELECT sum(total) FROM invoices"},
)


def _user(user_id="alice"):
    return User(id=user_id, email=f"{user_id}@example.com", group_memberships=["user"])


def _context(memory, user_id="alice"):
    return ToolContext(
        user=_user(user_id), conversation_id="c", request_id="r", agent_memory=memory
    )


def _memory():
    memory = MagicMock(spec=AgentMemory)
    memory.save_tool_usage = AsyncMock()
    return memory


async def test_default_saves_immediately():
    memory = _memory()

    await SaveQuestionToolArgsTool().execute(_context(memory), ARGS)

    memory.save_tool_usage.assert_awaited_once()


async def test_require_approval_does_not_save_and_shows_button():
    memory = _memory()
    tool = SaveQuestionToolArgsTool(require_approval=True)

    result = await tool.execute(_context(memory), ARGS)

    memory.save_tool_usage.assert_not_awaited()
    button = result.ui_component.rich_component
    assert isinstance(button, ButtonComponent)
    assert button.data["action"].startswith("/save_memory ")


async def test_approve_saves_once_for_same_user_only():
    memory = _memory()
    tool = SaveQuestionToolArgsTool(require_approval=True)
    result = await tool.execute(_context(memory), ARGS)
    pending_id = result.ui_component.rich_component.data["action"].split()[1]

    assert await tool.approve(pending_id, _context(memory, "mallory")) is False
    memory.save_tool_usage.assert_not_awaited()

    assert await tool.approve(pending_id, _context(memory, "alice")) is True
    memory.save_tool_usage.assert_awaited_once()
    assert memory.save_tool_usage.await_args.kwargs["args"] == ARGS.args

    assert (
        await tool.approve(pending_id, _context(memory, "alice")) is False
    )  # one-time
    memory.save_tool_usage.assert_awaited_once()


async def test_save_memory_command_via_workflow_handler():
    memory = _memory()
    tool = SaveQuestionToolArgsTool(require_approval=True)
    result = await tool.execute(_context(memory), ARGS)
    command = result.ui_component.rich_component.data["action"]

    registry = ToolRegistry()  # real registry: it wraps tools that have access groups
    registry.register_local_tool(tool, access_groups=["user"])
    agent = SimpleNamespace(tool_registry=registry, agent_memory=memory)
    conversation = SimpleNamespace(id="c")

    handled = await DefaultWorkflowHandler().try_handle(
        agent, _user("alice"), conversation, command
    )

    assert handled.should_skip_llm is True
    assert "Saved to memory" in handled.components[0].rich_component.content
    memory.save_tool_usage.assert_awaited_once()


async def test_legacy_adapter_config_enables_approval():
    import sys

    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from test_security_sql_read_only import _LegacyVanna
    from vanna.legacy.adapter import LegacyVannaAdapter

    default = LegacyVannaAdapter(_LegacyVanna("SELECT 1"))
    approval = LegacyVannaAdapter(
        _LegacyVanna("SELECT 1", config={"require_memory_approval": True})
    )

    def save_tool(adapter):
        return adapter._tools["save_question_tool_args"]._wrapped_tool

    assert save_tool(default).require_approval is False
    assert save_tool(approval).require_approval is True
