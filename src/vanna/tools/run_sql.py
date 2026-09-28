"""Generic SQL query execution tool with dependency injection."""

from typing import Any, Dict, List, Optional, Type, cast
import re
import uuid
from vanna.core.tool import Tool, ToolContext, ToolResult
from vanna.components import (
    UiComponent,
    DataFrameComponent,
    NotificationComponent,
    ComponentType,
    SimpleTextComponent,
)
from vanna.capabilities.sql_runner import SqlRunner, RunSqlToolArgs
from vanna.capabilities.file_system import FileSystem
from vanna.integrations.local import LocalFileSystem
from vanna.utils.sql_safety import ensure_read_only_sql

# Catalog tables/commands that describe the database structure rather than business data
_SCHEMA_QUERY = re.compile(
    r"\b(information_schema|sqlite_master|sqlite_schema|pg_catalog|pg_tables|pg_class"
    r"|pg_attribute|sys\.(tables|columns|objects|schemas)|all_tables|user_tables"
    r"|all_tab_columns|user_tab_columns|all_views|system\.(tables|columns)"
    r"|duckdb_tables|duckdb_columns|table_info|pragma_\w+)\b"
    r"|^\s*(show|describe|desc|pragma)\b",
    re.IGNORECASE,
)


def is_schema_query(sql: str) -> bool:
    """True if the query inspects database structure (tables, columns) - vanna-ai/vanna#1105."""
    return bool(_SCHEMA_QUERY.search(sql or ""))


class RunSqlTool(Tool[RunSqlToolArgs]):
    """Tool that executes SQL queries using an injected SqlRunner implementation."""

    def __init__(
        self,
        sql_runner: SqlRunner,
        file_system: Optional[FileSystem] = None,
        custom_tool_name: Optional[str] = None,
        custom_tool_description: Optional[str] = None,
        allow_write_sql: bool = False,
    ):
        """Initialize the tool with a SqlRunner implementation.

        Args:
            sql_runner: SqlRunner implementation that handles actual query execution
            file_system: FileSystem implementation for saving results (defaults to LocalFileSystem)
            custom_tool_name: Optional custom name for the tool (overrides default "run_sql")
            custom_tool_description: Optional custom description for the tool (overrides default description)
            allow_write_sql: Allow non-SELECT statements (INSERT, UPDATE, DDL, ...). Off by default
                because the SQL comes from the LLM and can be steered by prompt injection.
        """
        self.sql_runner = sql_runner
        self.allow_write_sql = allow_write_sql
        self.file_system = file_system or LocalFileSystem()
        self._custom_name = custom_tool_name
        self._custom_description = custom_tool_description

    @property
    def name(self) -> str:
        return self._custom_name if self._custom_name else "run_sql"

    @property
    def description(self) -> str:
        return (
            self._custom_description
            if self._custom_description
            else "Execute SQL queries against the configured database"
        )

    def get_args_schema(self) -> Type[RunSqlToolArgs]:
        return RunSqlToolArgs

    async def execute(self, context: ToolContext, args: RunSqlToolArgs) -> ToolResult:
        """Execute a SQL query using the injected SqlRunner."""
        try:
            if not self.allow_write_sql:
                ensure_read_only_sql(args.sql)

            # Use the injected SqlRunner to execute the query
            df = await self.sql_runner.run_sql(args, context)

            # Determine query type
            query_type = args.sql.strip().upper().split()[0]

            if query_type == "SELECT":
                # Handle SELECT queries with results
                if df.empty:
                    result = "Query executed successfully. No rows returned."
                    ui_component = UiComponent(
                        rich_component=DataFrameComponent(
                            rows=[],
                            columns=[],
                            title="Query Results",
                            description="No rows returned",
                        ),
                        simple_component=SimpleTextComponent(text=result),
                    )
                    metadata = {
                        "row_count": 0,
                        "columns": [],
                        "query_type": query_type,
                        "results": [],
                    }
                else:
                    # Convert DataFrame to records
                    results_data = df.to_dict("records")
                    columns = df.columns.tolist()
                    row_count = len(df)

                    # Write DataFrame to CSV file for downstream tools
                    file_id = str(uuid.uuid4())[:8]
                    filename = f"query_results_{file_id}.csv"
                    csv_content = df.to_csv(index=False)
                    await self.file_system.write_file(
                        filename, csv_content, context, overwrite=True
                    )

                    # Create result text for LLM with truncated results
                    results_preview = csv_content
                    if len(results_preview) > 1000:
                        results_preview = (
                            results_preview[:1000]
                            + "\n(Results truncated to 1000 characters. FOR LARGE RESULTS YOU DO NOT NEED TO SUMMARIZE THESE RESULTS OR PROVIDE OBSERVATIONS. THE NEXT STEP SHOULD BE A VISUALIZE_DATA CALL)"
                        )

                    result = f"{results_preview}\n\nResults saved to file: {filename}\n\n**IMPORTANT: FOR VISUALIZE_DATA USE FILENAME: {filename}**"

                    # Create DataFrame component for UI
                    dataframe_component = DataFrameComponent.from_records(
                        records=cast(List[Dict[str, Any]], results_data),
                        title="Query Results",
                        description=f"SQL query returned {row_count} rows with {len(columns)} columns",
                    )

                    ui_component = UiComponent(
                        rich_component=dataframe_component,
                        simple_component=SimpleTextComponent(text=result),
                    )

                    metadata = {
                        "row_count": row_count,
                        "columns": columns,
                        "query_type": query_type,
                        "results": results_data,
                        "output_file": filename,
                    }
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
                # The SqlRunner should return a DataFrame with affected row count
                rows_affected = len(df) if not df.empty else 0
                result = (
                    f"Query executed successfully. {rows_affected} row(s) affected."
                )

                metadata = {"rows_affected": rows_affected, "query_type": query_type}
                ui_component = UiComponent(
                    rich_component=NotificationComponent(
                        type=ComponentType.NOTIFICATION, level="success", message=result
                    ),
                    simple_component=SimpleTextComponent(text=result),
                )

            # The agent hides these results from users without the "schema_details" UI feature
            metadata["contains_schema_details"] = is_schema_query(args.sql)

            return ToolResult(
                success=True,
                result_for_llm=result,
                ui_component=ui_component,
                metadata=metadata,
            )

        except Exception as e:
            error_message = f"Error executing query: {str(e)}"
            return ToolResult(
                success=False,
                result_for_llm=error_message,
                ui_component=UiComponent(
                    rich_component=NotificationComponent(
                        type=ComponentType.NOTIFICATION,
                        level="error",
                        message=error_message,
                    ),
                    simple_component=SimpleTextComponent(text=error_message),
                ),
                error=str(e),
                metadata={"error_type": "sql_error"},
            )
