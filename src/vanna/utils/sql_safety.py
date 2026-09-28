"""Read-only guard for LLM-generated SQL (vanna-ai/vanna#1078).

LLM output is attacker-influenced: a prompt injection can make the model emit
`DROP TABLE`, stacked queries, or database-specific tricks that run shell
commands (e.g. Oracle `DBMS_SCHEDULER`). By default only a single read-only
statement is allowed. Users who really want the LLM to modify data can opt out
with `allow_write_sql=True`.

This is defence in depth. The real protection is connecting with a database
user that only has read permissions.
"""

import sqlparse
from sqlparse import tokens

# Statements that only read metadata and are safe to run.
READ_ONLY_LEADING_KEYWORDS = {"SHOW", "DESCRIBE", "DESC"}

# Clauses/functions that write files, read server files, or run code even inside a SELECT.
DENIED_WORDS = {
    "INTO",  # SELECT ... INTO new_table / INTO OUTFILE / INTO DUMPFILE
    "LOAD_EXTENSION",  # SQLite
    "LOAD_FILE",  # MySQL
    "PG_READ_FILE",  # PostgreSQL
    "PG_READ_BINARY_FILE",
    "PG_LS_DIR",
    "PG_STAT_FILE",
    "LO_IMPORT",
    "LO_EXPORT",
    "DBLINK",
    "DBLINK_EXEC",
    "XP_CMDSHELL",  # SQL Server
    "SP_OACREATE",
    "OPENROWSET",
    "OPENDATASOURCE",
    "READ_CSV",  # DuckDB file readers
    "READ_CSV_AUTO",
    "READ_TEXT",
    "READ_BLOB",
    "READ_JSON",
    "READ_JSON_AUTO",
    "READ_PARQUET",
}
DENIED_PREFIXES = ("DBMS_", "UTL_")  # Oracle packages (DBMS_SCHEDULER, UTL_FILE, ...)

WRITE_SQL_HINT = (
    "Only read-only SELECT queries are allowed by default. "
    "Set allow_write_sql=True to let the LLM run other statements."
)


class UnsafeSqlError(ValueError):
    pass


def ensure_read_only_sql(sql: str) -> None:
    """Raise UnsafeSqlError unless `sql` is a single read-only statement."""
    statements = [s for s in sqlparse.parse(sql or "") if s.value.strip(" \t\r\n;")]

    if len(statements) != 1:
        raise UnsafeSqlError(
            f"Expected exactly one SQL statement, got {len(statements)}. {WRITE_SQL_HINT}"
        )

    statement = statements[0]
    first = statement.token_first(skip_cm=True, skip_ws=True)
    leading = first.normalized.upper() if first is not None else ""

    if statement.get_type() != "SELECT" and leading not in READ_ONLY_LEADING_KEYWORDS:
        raise UnsafeSqlError(
            f"'{leading or 'empty'}' statements are not allowed. {WRITE_SQL_HINT}"
        )

    for token in statement.flatten():
        if token.ttype in tokens.String or token.ttype in tokens.Comment:
            continue
        # Catches writes hidden inside a SELECT, e.g. WITH d AS (DELETE ... RETURNING *) SELECT ...
        if (token.ttype in tokens.Keyword.DML and token.normalized != "SELECT") or (
            token.ttype in tokens.Keyword.DDL
        ):
            raise UnsafeSqlError(f"'{token.value}' is not allowed. {WRITE_SQL_HINT}")
        word = token.value.strip('`"[]').upper()
        if word in DENIED_WORDS or word.startswith(DENIED_PREFIXES):
            raise UnsafeSqlError(f"'{token.value}' is not allowed. {WRITE_SQL_HINT}")


# Leading keywords of statements that return a result set but that sqlparse types as UNKNOWN
_ROW_RETURNING_KEYWORDS = {"SHOW", "DESCRIBE", "DESC", "EXPLAIN", "PRAGMA", "VALUES"}


def sql_returns_rows(sql: str) -> bool:
    """True if `sql` returns a result set (SELECT, WITH ... SELECT, SHOW, ...).

    Unlike checking the first word, this handles CTEs and leading comments.
    """
    statements = [s for s in sqlparse.parse(sql or "") if s.value.strip(" \t\r\n;")]
    if not statements:
        return False
    statement = statements[-1]
    if statement.get_type() == "SELECT":
        return True
    first = statement.token_first(skip_cm=True, skip_ws=True)
    return first is not None and first.normalized.upper() in _ROW_RETURNING_KEYWORDS
