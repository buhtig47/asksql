"""Guarded execution of LLM-generated Plotly code (vanna-ai/vanna#1098).

`get_plotly_figure` runs Python written by the LLM, and the LLM prompt can be
influenced by users (e.g. the Flask `chart_instructions` query param). Without
a guard, a prompt injection becomes remote code execution.

This is defence in depth, NOT a true sandbox - CPython cannot be sandboxed
in-process. It closes the easy paths: arbitrary imports, `_`/dunder tricks,
file/network IO helpers, dangerous builtins and access to vanna's module globals.
"""

import ast
import builtins

import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go

ALLOWED_IMPORT_ROOTS = {"plotly", "pandas", "numpy", "math"}

# Attribute/import names that lead to the OS, the interpreter, or file/network IO.
DENIED_NAMES = {
    # modules reachable as attributes of other modules
    "os",
    "sys",
    "subprocess",
    "builtins",
    "importlib",
    "io",
    "ctypes",
    "ctypeslib",
    "socket",
    "shutil",
    "pickle",
    "marshal",
    "pty",
    "requests",
    # process / code execution
    "system",
    "popen",
    "Popen",
    "spawn",
    "fork",
    "eval",
    "exec",
    "compile",
    "query",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "open",
    "input",
    "breakpoint",
    # pandas / numpy / plotly file IO
    "to_csv",
    "to_excel",
    "to_json",
    "to_html",
    "to_parquet",
    "to_pickle",
    "to_sql",
    "to_hdf",
    "to_feather",
    "to_stata",
    "to_xml",
    "to_orc",
    "to_latex",
    "to_markdown",
    "to_string",
    "to_clipboard",
    "tofile",
    "write_html",
    "write_image",
    "write_json",
    "save",
    "savez",
    "savez_compressed",
    "savetxt",
    "load",
    "loadtxt",
    "genfromtxt",
    "fromfile",
    "memmap",
}

SAFE_BUILTIN_NAMES = [
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "filter",
    "float",
    "int",
    "isinstance",
    "len",
    "list",
    "map",
    "max",
    "min",
    "print",
    "range",
    "reversed",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
    "Exception",
]


class UnsafePlotlyCodeError(ValueError):
    pass


def _is_denied(name: str) -> bool:
    # A bare "_" is the usual throwaway loop variable; any other leading "_" is private/dunder.
    if name != "_" and name.startswith("_"):
        return True
    return name in DENIED_NAMES or name.startswith("read_")


def validate_plotly_code(code: str) -> None:
    """Raise UnsafePlotlyCodeError if `code` uses anything outside the allowed subset."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise UnsafePlotlyCodeError(f"invalid Python: {e}") from e

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORT_ROOTS:
                    raise UnsafePlotlyCodeError(
                        f"import of '{alias.name}' is not allowed"
                    )
        elif isinstance(node, ast.ImportFrom):
            if (
                node.level
                or (node.module or "").split(".")[0] not in ALLOWED_IMPORT_ROOTS
            ):
                raise UnsafePlotlyCodeError(
                    f"import from '{node.module}' is not allowed"
                )
            for alias in node.names:
                if alias.name == "*" or _is_denied(alias.name):
                    raise UnsafePlotlyCodeError(
                        f"import of '{alias.name}' is not allowed"
                    )
        elif isinstance(node, ast.Attribute) and _is_denied(node.attr):
            raise UnsafePlotlyCodeError(f"access to '.{node.attr}' is not allowed")
        elif isinstance(node, ast.Name) and _is_denied(node.id):
            raise UnsafePlotlyCodeError(f"use of '{node.id}' is not allowed")


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level != 0 or name.split(".")[0] not in ALLOWED_IMPORT_ROOTS:
        raise ImportError(f"import of '{name}' is not allowed in chart code")
    return builtins.__import__(name, globals, locals, fromlist, level)


def exec_plotly_code(code: str, df: pd.DataFrame):
    """Validate and run LLM-generated Plotly code; return the `fig` it defines (or None)."""
    validate_plotly_code(code)

    safe_builtins = {name: getattr(builtins, name) for name in SAFE_BUILTIN_NAMES}
    safe_builtins["__import__"] = _restricted_import

    namespace = {
        "__builtins__": safe_builtins,
        "df": df,
        "pd": pd,
        "plotly": plotly,
        "px": px,
        "go": go,
    }
    exec(code, namespace)
    return namespace.get("fig")
