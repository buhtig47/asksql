# Changelog

Changes in this community-maintained fork, relative to the last upstream Vanna release (2.0.2).

## Unreleased

### Security
- **LLM-generated SQL is now read-only by default** (vanna-ai/vanna#1078). Only a single `SELECT` / `WITH … SELECT` (plus `SHOW` / `DESCRIBE`) is executed. Writes, DDL, stacked queries, writes hidden in CTEs, `SELECT … INTO`, and known file/shell helpers (`DBMS_*`, `UTL_*`, `pg_read_file`, `load_extension`, `xp_cmdshell`, DuckDB `read_csv`, …) are rejected. Applies to legacy `ask()`, the legacy Flask server, the legacy adapter and the v2 `RunSqlTool`.
- **LLM-generated Plotly code is no longer run with full access** (vanna-ai/vanna#1098). `get_plotly_figure` validates the code and runs it with restricted builtins, without vanna's module globals (`os`, `requests`, …). Rejected code falls back to the automatic chart.
- **Fixed SQL injection in the BigQuery vector store** (CVE-2026-4229, vanna-ai/vanna#1121, #1098). `remove_training_data` and `fetch_similar_training_data` now pass values as query parameters.

### Breaking changes
- If you relied on the LLM running `INSERT` / `UPDATE` / `DELETE` / DDL, opt back in:
  - Legacy (1.x API): `MyVanna(config={..., "allow_write_sql": True})`
  - v2: `RunSqlTool(sql_runner=..., allow_write_sql=True)`

  Recommended in any case: connect with a database user that only has read permissions.

### Fixed
- Test suite: `tests/test_agents.py` helper was collected as a test; Azure OpenAI tests patched the wrong import target.
