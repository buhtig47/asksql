# TODO

Baseline: `pytest tests/` on Python 3.13 → 41 failed, 167 passed, 47 skipped, 1 error (28-09-2026)
Now: 29 failed (all missing optional packages), 224 passed, 47 skipped

## Security (the fork's main selling point)
- [x] #1121 CVE-2026-4229 — SQL injection in BigQuery `remove_training_data`
- [x] #1098 — same BigQuery injection + unsafe `exec()` of LLM-generated Plotly code (now guarded by `legacy/base/safe_exec.py`)
- [x] #1078 — LLM-generated SQL is now read-only by default (`utils/sql_safety.py`, opt out with `allow_write_sql=True`)
- [ ] #1098 leftover — `training_data_type` interpolated into SQL in `bigquery_vector.py` `fetch_similar_training_data`

## Test fixes
- [x] B. Azure OpenAI tests patched the wrong target (lazy import) → patch `openai.AzureOpenAI`
- [x] C. `test_agent_top_artist` was a helper collected as a test → renamed to `check_agent_top_artist`

## Not bugs (missing optional packages)
- ~29 tests fail with ImportError: ollama, chromadb, psycopg2, snowflake, mysql, duckdb, oracle, bigquery, pyodbc, pyhive
- Our scope needs only `chromadb` and `psycopg2-binary`

## Later
- Tests that need an optional package should **skip**, not fail, when it is missing
