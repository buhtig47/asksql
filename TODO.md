# TODO

Baseline: `pytest tests/` on Python 3.13 → 41 failed, 167 passed, 47 skipped, 1 error (28-09-2026)
Now: 0 failed, 225 passed, 76 skipped (optional packages / API keys missing → skipped via tests/conftest.py)

## Security (the fork's main selling point)
- [x] #1121 CVE-2026-4229 — SQL injection in BigQuery `remove_training_data`
- [x] #1098 — same BigQuery injection + unsafe `exec()` of LLM-generated Plotly code (now guarded by `legacy/base/safe_exec.py`)
- [x] #1078 — LLM-generated SQL is now read-only by default (`utils/sql_safety.py`, opt out with `allow_write_sql=True`)
- [x] #1098 leftover — `training_data_type` in BigQuery `fetch_similar_training_data` now a query parameter

## Test fixes
- [x] B. Azure OpenAI tests patched the wrong target (lazy import) → patch `openai.AzureOpenAI`
- [x] C. `test_agent_top_artist` was a helper collected as a test → renamed to `check_agent_top_artist`

## Infra
- [x] Rename distribution to `asksql` (keeps `import vanna`)
- [x] Tests needing optional packages skip instead of fail
- [x] CI: GitHub Actions on Python 3.10–3.13 (ruff + pytest)
- [ ] Run CI with `chromadb` + `psycopg2-binary` installed too (our supported integrations)
- [x] Release workflow uses PyPI trusted publishing (no token)
- [x] PyPI pending publisher added; GitHub release v2.1.0 created and published to PyPI
- [x] Enable GitHub Issues on the fork

## Bugs / features
- [x] #1103 optional human approval before saving to memory (`require_approval=True`)
- [x] #1105 schema lookup results hidden from non-admins (`schema_details` UI feature)
- [ ] RunSqlTool treats `WITH …` / `SHOW` / `DESCRIBE` results as "rows affected" (LLM never sees the data)
- [ ] #997 FastAPI server missing endpoints

## Launch prep
- [x] MIGRATING_FROM_VANNA.md (verified: wrong uninstall order breaks install → force-reinstall fixes)
- [x] README badges + migration guide link
- [ ] Draft Show HN + r/selfhosted posts (Ayush approves before posting)
- [ ] Consider: alias `vanna.openai` → `vanna.legacy.openai` etc. so Vanna 0.x imports work unchanged
