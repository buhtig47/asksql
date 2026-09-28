# Migrating from Vanna to asksql

asksql is a drop-in replacement for [Vanna](https://github.com/vanna-ai/vanna) 2.0.x. It is published under a new name on PyPI, but the Python import name is still `vanna`, so your code does not change.

- [From Vanna 2.0.x](#from-vanna-20x) (most users)
- [From Vanna 0.x](#from-vanna-0x)
- [Behaviour changes to know about](#behaviour-changes-to-know-about)
- [Troubleshooting](#troubleshooting)

## From Vanna 2.0.x

**1. Swap the package.** Uninstall Vanna *first*, then install asksql:

```bash
pip uninstall vanna
pip install asksql
```

The order matters. Both packages ship the same `vanna/` folder, so uninstalling Vanna *after* installing asksql deletes asksql's files too (see [Troubleshooting](#troubleshooting)).

**2. Rename extras in your requirements.** `vanna[...]` would pull upstream Vanna back in:

```diff
- vanna[postgres,openai]==2.0.2
+ asksql[postgres,openai]==2.1.0
```

The extra names are the same as before (`postgres`, `openai`, `anthropic`, `chromadb`, `fastapi`, `flask`, …).

**3. That's it.** `import vanna`, `from vanna import Agent`, `vanna.legacy.*` and the `vanna` CLI command all keep working. There is also a new `asksql` CLI command that does the same thing.

Check that it worked:

```bash
python -c "import vanna, importlib.metadata as m; print(m.version('asksql'), vanna.__version__)"
# 2.1.0 2.1.0
```

## From Vanna 0.x

Vanna 2.0 (upstream) moved the 0.x classes under `vanna.legacy`. asksql keeps that layout, so update your imports once:

| Vanna 0.x | asksql (and Vanna 2.0) |
|---|---|
| `from vanna.base import VannaBase` | `from vanna.legacy.base import VannaBase` |
| `from vanna.openai import OpenAI_Chat` | `from vanna.legacy.openai import OpenAI_Chat` |
| `from vanna.anthropic import Anthropic_Chat` | `from vanna.legacy.anthropic import Anthropic_Chat` |
| `from vanna.ollama import Ollama` | `from vanna.legacy.ollama import Ollama` |
| `from vanna.chromadb import ChromaDB_VectorStore` | `from vanna.legacy.chromadb import ChromaDB_VectorStore` |
| `from vanna.pgvector import PG_VectorStore` | `from vanna.legacy.pgvector import PG_VectorStore` |
| `from vanna.flask import VannaFlaskApp` | `from vanna.legacy.flask import VannaFlaskApp` |

The rest of your code (`class MyVanna(ChromaDB_VectorStore, OpenAI_Chat)`, `vn.connect_to_postgres(...)`, `vn.train(...)`, `vn.ask(...)`) stays the same.

Then swap the package as described [above](#from-vanna-20x).

To move to the newer Agent API (streaming, web component, user-aware tools), see the upstream [Vanna 0.x → 2.0 guide](MIGRATION_GUIDE.md). It applies to asksql unchanged.

## Behaviour changes to know about

These are deliberate security fixes. See [CHANGELOG.md](CHANGELOG.md) for details.

**LLM-generated SQL is read-only by default.** `vn.ask()`, the Flask app and `RunSqlTool` only run a single `SELECT` (or `SHOW` / `DESCRIBE`). If the LLM produces `DELETE`, `DROP`, stacked queries and so on, you get this instead of a run:

```
Couldn't run sql:  'DROP' statements are not allowed. Only read-only SELECT queries are allowed by default. Set allow_write_sql=True to let the LLM run other statements.
```

If your app really needs the LLM to write data, opt back in:

```python
# Vanna 0.x-style API
vn = MyVanna(config={"model": "gpt-4o", "allow_write_sql": True})

# Agent API
RunSqlTool(sql_runner=runner, allow_write_sql=True)
```

Either way, connect with a database user that only has the permissions the app needs.

**LLM-generated chart code runs in a restricted environment.** Plotly code from the LLM can use `df`, `px`, `go`, `pd` and imports from `plotly`, `pandas`, `numpy` and `math`. Code that tries anything else (other imports, file access, `os`, dunder attributes) is rejected, and you get the automatic chart instead.

**Schema lookups are hidden from non-admin users (Agent API).** When the LLM looks up tables and columns (`information_schema`, `sqlite_master`, `SHOW TABLES`, …) before answering, users outside the `admin` group no longer see that listing in the chat. They still see the answer. To show it to everyone:

```python
config = AgentConfig()
config.ui_features.register_feature("schema_details", [])  # [] = all users
```

**FastAPI CORS no longer allows credentials from any origin.** If your frontend runs on a different origin than the server and uses cookie auth, list it: `VannaFastAPIServer(agent, config={"cors": {"allow_origins": ["https://app.example.com"]}})`. See [SERVER_API.md](SERVER_API.md#cors).

## Troubleshooting

**`import vanna` fails or `vanna` has no `__version__` after migrating.** You probably ran `pip uninstall vanna` *after* `pip install asksql`, which deleted the shared files. Reinstall:

```bash
pip install --force-reinstall --no-deps asksql
```

**Not sure which package is installed?**

```bash
pip show asksql vanna
```

Only `asksql` should be listed. If both are listed, run `pip uninstall vanna` and then the reinstall command above.

**Something else broke?** [Open an issue](https://github.com/buhtig47/asksql/issues) with your Vanna version, your asksql version and the error.
