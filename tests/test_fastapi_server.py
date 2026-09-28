"""VannaFastAPIServer endpoints (vanna-ai/vanna#997) and CORS defaults."""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from vanna import Agent  # noqa: E402
from vanna.core.llm import LlmService  # noqa: E402
from vanna.core.llm.models import LlmResponse, LlmStreamChunk  # noqa: E402
from vanna.core.registry import ToolRegistry  # noqa: E402
from vanna.core.user import User, UserResolver  # noqa: E402
from vanna.integrations.local.agent_memory import DemoAgentMemory  # noqa: E402
from vanna.servers.fastapi import VannaFastAPIServer  # noqa: E402

EVIL = "https://evil.example"


class _Llm(LlmService):
    async def send_request(self, request):
        return LlmResponse(content="Hello from the agent", finish_reason="stop")

    async def stream_request(self, request):
        yield LlmStreamChunk(content="Hello from the agent", finish_reason="stop")

    async def validate_tools(self, tools):
        return []


class _Users(UserResolver):
    async def resolve_user(self, request_context):
        return User(id="u", email="u@example.com", group_memberships=["user"])


def _client(config=None):
    agent = Agent(
        llm_service=_Llm(),
        tool_registry=ToolRegistry(),
        user_resolver=_Users(),
        agent_memory=DemoAgentMemory(),
    )
    return TestClient(VannaFastAPIServer(agent, config).create_app())


def test_health():
    response = _client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "vanna"}


def test_chat_poll_returns_all_chunks():
    response = _client().post("/api/vanna/v2/chat_poll", json={"message": "hi"})

    assert response.status_code == 200
    body = response.json()
    texts = [c["simple"]["text"] for c in body["chunks"] if c.get("simple")]
    assert "Hello from the agent" in texts
    assert body["total_chunks"] == len(body["chunks"])


def test_chat_sse_streams_until_done():
    response = _client().post("/api/vanna/v2/chat_sse", json={"message": "hi"})

    events = [line for line in response.text.splitlines() if line.startswith("data:")]
    assert response.status_code == 200
    assert events[-1] == "data: [DONE]"


def test_default_cors_does_not_share_credentials_with_any_origin():
    response = _client().post(
        "/api/vanna/v2/chat_poll",
        json={"message": "hi"},
        headers={"Origin": EVIL, "Cookie": "session=secret"},
    )

    # Without allow-credentials the browser won't let evil.example read a cookie-authenticated answer
    assert response.headers.get("access-control-allow-credentials") != "true"


def test_explicit_origins_keep_credentials():
    client = _client({"cors": {"allow_origins": ["https://app.example.com"]}})

    allowed = client.options(
        "/api/vanna/v2/chat_poll",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    evil = client.options(
        "/api/vanna/v2/chat_poll",
        headers={"Origin": EVIL, "Access-Control-Request-Method": "POST"},
    )

    assert allowed.headers.get("access-control-allow-credentials") == "true"
    assert evil.headers.get("access-control-allow-origin") is None


def test_wildcard_with_credentials_warns():
    with pytest.warns(UserWarning, match="any website"):
        _client({"cors": {"allow_origins": ["*"], "allow_credentials": True}})
