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