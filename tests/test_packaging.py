"""The package is published as `asksql` but imported as `vanna`."""

import re
from pathlib import Path

import vanna


def test_version_matches_pyproject():
    pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    # tomllib is 3.11+, and CI also runs 3.10
    name = re.search(r'^name = "(.+)"$', pyproject, re.MULTILINE).group(1)
    version = re.search(r'^version = "(.+)"$', pyproject, re.MULTILINE).group(1)

    assert name == "asksql"
    assert vanna.__version__ == version
