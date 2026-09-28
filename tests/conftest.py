"""
Pytest configuration and shared fixtures for Vanna v2 test suite.
"""

import os
import pytest
import sqlite3
from pathlib import Path

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "anthropic: marks tests requiring Anthropic API key"
    )
    config.addinivalue_line("markers", "openai: marks tests requiring OpenAI API key")
    config.addinivalue_line(
        "markers", "azureopenai: marks tests requiring Azure OpenAI API key"
    )
    config.addinivalue_line("markers", "gemini: marks tests requiring Google API key")
    config.addinivalue_line("markers", "ollama: marks tests requiring Ollama")
    config.addinivalue_line("markers", "chromadb: marks tests requiring ChromaDB")
    config.addinivalue_line("markers", "legacy: marks tests for LegacyVannaAdapter")


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests if required API keys are missing."""
    for item in items:
        # Skip Anthropic tests if no API key
        if "anthropic" in item.keywords:
            if not os.getenv("ANTHROPIC_API_KEY"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="ANTHROPIC_API_KEY environment variable not set"
                    )
                )

        # Skip OpenAI tests if no API key
        if "openai" in item.keywords:
            if not os.getenv("OPENAI_API_KEY"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="OPENAI_API_KEY environment variable not set"
                    )
                )

        # Skip Azure OpenAI tests if no API key
        if "azureopenai" in item.keywords:
            if not os.getenv("AZURE_OPENAI_API_KEY"):
                item.add_marker(
                    pytest.mark.skip(
                        reason="AZURE_OPENAI_API_KEY environment variable not set"
                    )
                )

        # Skip Gemini tests if no API key
        if "gemini" in item.keywords:
            if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
                item.add_marker(
                    pytest.mark.skip(
                        reason="GOOGLE_API_KEY or GEMINI_API_KEY environment variable not set"
                    )
                )


# Optional integrations: tests that need them are skipped (not failed) when not installed.
OPTIONAL_MODULES = {
    "chromadb",
    "clickhouse_connect",
    "duckdb",
    "google",
    "ollama",
    "oracledb",
    "psycopg2",
    "pyhive",
    "pymysql",
    "pyodbc",
    "snowflake",
}


def _is_missing_optional_dependency(exc):
    """True if `exc` (or its cause) is vanna's "X package is required. Install with: pip install ..." error."""
    while exc is not None:
        if (
            isinstance(exc, ModuleNotFoundError)
            and (exc.name or "").split(".")[0] in OPTIONAL_MODULES
        ):
            return True
        if isinstance(
            exc, (ImportError, pytest.fail.Exception)
        ) and "pip install" in str(exc):
            return True
        exc = exc.__cause__ or exc.__context__
    return False


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if (
        report.failed
        and call.excinfo is not None
        and _is_missing_optional_dependency(call.excinfo.value)
    ):
        report.outcome = "skipped"
        reason = str(call.excinfo.value).splitlines()[0]
        report.longrepr = (
            str(item.path),
            item.location[1] or 0,
            f"Skipped: optional dependency missing: {reason}",
        )


@pytest.fixture(scope="session")
def chinook_db(tmp_path_factory):
    """
    Downloads the Chinook SQLite database and returns a SqliteRunner.

    Uses session scope so the database is only downloaded once per test session.
    """
    import httpx
    from vanna.integrations.sqlite import SqliteRunner

    tmp_path = tmp_path_factory.mktemp("data")
    db_path = tmp_path / "Chinook.sqlite"

    # Download the database
    response = httpx.get("https://vanna.ai/Chinook.sqlite")
    response.raise_for_status()

    db_path.write_bytes(response.content)

    return SqliteRunner(database_path=str(db_path))
