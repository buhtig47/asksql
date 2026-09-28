# Learning Log

Rule: 3 lines per day/issue — what I learned.

## 28-09-2026 — Setup
1. forked the repo and cloned it on local
2. setup on local; installed all dependencies, and packages
3. ran the test to uncover pending issues to track them

renamed test_agent_top_artist to check_agent_top_artist so it does not get treated as a test case

replaced vanna.integrations.azureopenai.llm.AzureOpenAI with openai.AzureOpenAI

never use the user inputs as f-strings in SQL. Use parameterised query instead, so the input gets always treated as data and not code.   

## 28-09-2026 — #1098 exec() on LLM code
1. LLM output is user input: anyone who can influence the prompt (e.g. a URL param) controls the code, so `exec()` on it = remote code execution.
2. `exec(code, globals())` hands the code every module the file imported (`os`, `requests`) — always pass a small, explicit namespace instead.
3. Python can't be fully sandboxed in-process; checking the code with `ast` + restricted builtins is defence in depth, not a guarantee.

## 28-09-2026 — #1078 LLM SQL read-only
1. Checking only the first word ("starts with SELECT") is not enough: `WITH d AS (DELETE … RETURNING *) SELECT …` and `SELECT … INTO OUTFILE` both start like reads.
2. Parse SQL with a real tokenizer (`sqlparse`) so keywords inside string literals (`WHERE note = 'DROP TABLE'`) are treated as data, not flagged.
3. Secure-by-default can break users, so ship it with a one-line opt-out (`allow_write_sql=True`) and document it in the CHANGELOG.