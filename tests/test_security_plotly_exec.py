"""Regression tests for unsafe exec() of LLM-generated Plotly code (vanna-ai/vanna#1098)."""

import pandas as pd
import plotly.graph_objects as go
import pytest

from vanna.legacy.base import VannaBase
from vanna.legacy.base.safe_exec import UnsafePlotlyCodeError, validate_plotly_code

MARKER = "VANNA_PWNED"


@pytest.fixture
def df():
    return pd.DataFrame({"name": ["a", "b", "c"], "sales": [3, 1, 2]})


def get_figure(code, df):
    # get_plotly_figure doesn't use `self`, and VannaBase is abstract
    return VannaBase.get_plotly_figure(None, plotly_code=code, df=df, dark_mode=False)


# --- normal chart code must keep working (Vanna compatibility) ---


@pytest.mark.parametrize(
    "code",
    [
        "fig = px.bar(df, x='name', y='sales')",
        "import plotly.express as px\nfig = px.bar(df, x='name', y='sales')",
        "import plotly.graph_objects as go\nfig = go.Figure(go.Bar(x=df['name'], y=df['sales']))",
        "d = df.sort_values('sales')\nfig = px.bar(d, x='name', y=[v * 2 for v in d['sales']])",
    ],
)
def test_normal_chart_code_still_runs(code, df):
    fig = get_figure(code, df)

    assert isinstance(fig, go.Figure)
    assert fig.data[0].type == "bar"  # the LLM's chart, not the scatter/pie fallback


# --- attacks must not run ---


@pytest.mark.parametrize(
    "code",
    [
        # vanna's module globals (os, requests, ...) used to be exposed to exec
        f"os.environ['{MARKER}'] = '1'",
        f"import os\nos.environ['{MARKER}'] = '1'",
        f"__import__('os').environ['{MARKER}'] = '1'",
        f"pd.io.common.os.environ['{MARKER}'] = '1'",
        # classic dunder sandbox escape
        "().__class__.__base__.__subclasses__()",
    ],
)
def test_malicious_code_is_not_executed(code, df, monkeypatch):
    monkeypatch.delenv(MARKER, raising=False)

    with pytest.raises(UnsafePlotlyCodeError):
        validate_plotly_code(code)

    fig = get_figure(code, df)  # falls back to an auto-generated chart instead

    assert MARKER not in __import__("os").environ
    assert isinstance(fig, go.Figure)


def test_file_write_is_blocked(df, tmp_path):
    target = tmp_path / "leak.csv"

    get_figure(f"df.to_csv(r'{target}')\nfig = px.bar(df, x='name', y='sales')", df)

    assert not target.exists()


def test_disallowed_import_blocked_at_runtime_too(df):
    # even if validation were bypassed, the restricted __import__ refuses it
    from vanna.legacy.base.safe_exec import _restricted_import

    with pytest.raises(ImportError):
        _restricted_import("subprocess")
