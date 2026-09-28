# Project: Community-maintained fork of Vanna

> Put this file in the root of the forked repo. Claude Code reads it at the start of every session.

## What this project is
- A fork of **vanna-ai/vanna** (open-source Text-to-SQL Python library, ~23K GitHub stars, MIT license, last version 2.0.2).
- The original repo was **archived on 29 March 2026**. ~227 issues were left open. Users are looking for a maintained alternative.
- **Goal:** become the maintained, lightweight, secure, Vanna-compatible successor.
  - Hook: "Vanna users — change one import, everything keeps working."
- Project name: `<NAME>` (not "vanna"). Keep the original MIT LICENSE and copyright line. README must credit Vanna.

## Who I am and how I want to work (MOST IMPORTANT)
**Primary goal: make this fork the maintained Vanna successor (users, stars, launch).** Learning and being part of the process is secondary — it must not slow the project down.

**Rules for Claude (Claude does the work):**
1. **Claude does all the work end-to-end** — code, tests, TODO/LEARNING_LOG updates, commits and pushes to my fork (`origin`). Don't hand me steps to run.
2. Decide what to do next yourself. Ask me only for real product decisions or anything irreversible/public beyond pushing to my fork (PyPI release, posting on HN/Reddit, opening upstream PRs/issues, renaming the repo).
3. After each piece of work, tell me briefly in simple Hinglish what changed and why, so I stay in the loop.
4. Prioritise what gets users to switch: security fixes, compatibility, migration guide, PyPI release, launch.
5. Keep answers short. I prefer Hinglish, casual and direct. Big plans overwhelm me.

## Workflow for every issue
1. Write the problem in one line
2. Reproduce it with a **failing test**
3. Find the cause, fix until the test passes
4. Verify: the new test fails on the old code, and the full suite has no new failures
5. Commit with a clear message and push
6. Add 3 lines to `LEARNING_LOG.md`: what was learned (not just what was done)

## Codebase map (src/vanna/)
| Folder | ~Lines | Priority |
|---|---|---|
| `core/` | 7,400 | **HIGH — the real engine** |
| `tools/` | 1,800 | **HIGH** |
| `servers/` | 1,500 | **HIGH** (FastAPI/Flask servers) |
| `integrations/` | 8,200 | Only focus on: sqlite, postgres, openai, anthropic, chromadb |
| `legacy/` | 11,000 | Ignore for now (old Vanna 1.x) |
| `examples/` | 4,400 | Ignore |

Suggested first learning task: trace ONE question end-to-end using **SQLite + OpenAI** with a debugger.

## Setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install openai
pytest tests/ -x
```
Do NOT install `.[all]` (35+ heavy dependencies). Some tests will fail (code is ~8 months stale) — list them in `TODO.md` instead of fixing immediately.

## Roadmap
**Weekend 1:** fork, setup, run tests, list failures in `TODO.md`, add "community-maintained fork, WIP" line to README.

**Weeks 1–3:** understand core, update dependencies.

**Weeks 4–6:** fix issues (difficulty ladder below), README, "Migrating from Vanna" guide, publish on PyPI under new name.

**Week 7:** launch — Hacker News (Show HN), r/selfhosted, r/LocalLLaMA, awesome-selfhosted / awesome-OSS-alternatives lists.

**After:** weekly issue replies, release every 2–4 weeks. Paid hosted version only after ~1,000+ stars.

**Kill rule:** if 3 months after launch there are few Vanna users and <200–300 stars, stop and rethink.

## Difficulty ladder (go up one step at a time)
1. Dependency updates + get tests green
2. Docs / README fixes
3. Small bugs (10–30 lines) — **first issue: #1112** (Legacy OpenAI_Chat: temperature=0.7 causes 400 with models that only support default)
4. Security fixes — the fork's biggest selling point:
   - #1121 SQL injection in `remove_training_data` (CVE-2026-4229)
   - #1098 SQL injection in Databricks/BigQuery vector stores + unsafe `exec()` on LLM output
   - #1078 Remote Code Execution report
5. Other bugs: #1105 (too much process data in chat page), #1103 (wrong SQL saved to memory without validation), #997 (FastAPI server missing endpoints)
6. Features: vLLM support (#1104), Vertex AI (#1085), multi-tenant (#914)

Original issue list (read-only, use as a wishlist): https://github.com/vanna-ai/vanna/issues

## Hard rules
- Personal laptop and personal time only. No employer code, data or devices.
- Never remove the MIT license or original copyright.
- Don't use the "Vanna" name or logo as our brand.
- Every fix gets a test.
