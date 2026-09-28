# TODO

Baseline: `pytest tests/` on Python 3.13 → 41 failed, 167 passed, 47 skipped, 1 error (28-09-2026)

## Real bugs (fix later, one at a time)

FIXED
### B. Azure OpenAI tests (12 failing)
- File: `tests/test_azureopenai_llm.py`
- Error: `module 'vanna.integrations.azureopenai.llm' does not have the attribute 'AzureOpenAI'`
- My hypothesis: I think ______ causes ______

FIXED
### C. `test_agent_top_artist` error
- File: `tests/test_agents.py:55`
- Error: `fixture 'agent' not found`
- My hypothesis: I think it is an import issue.

## Not bugs (missing optional packages)

### A. ~27 tests fail with ImportError
- ollama, chromadb, psycopg2, snowflake, mysql, duckdb, oracle, bigquery, pyodbc, pyhive
- Our scope needs only: `chromadb`, `psycopg2-binary` → install these later

## Later
- Tests that need an optional package should **skip**, not fail, when it is missing
