"""
Static SQL Validator
---------------------
Runs entirely in code, before the generated SQL ever reaches Snowflake.
No LLM call, no database round trip. This is the last line of defense
between an LLM-generated query and your production database.

Requires: pip install sqlglot
"""

import sqlglot
from sqlglot import exp

FORBIDDEN_STATEMENT_TYPES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter,
    exp.Create, exp.Merge, exp.Grant, exp.TruncateTable,
)

DEFAULT_ROW_LIMIT = 10_000


def validate_sql(sql: str, allowed_tables: list[str]) -> tuple[bool, str, str]:
    """
    Returns (is_valid, reason, possibly_modified_sql).

    Checks performed:
      1. Parses cleanly as Snowflake-dialect SQL.
      2. Is a single SELECT statement (no DDL/DML).
      3. Only references tables from `allowed_tables` (the exact set
         handed to the LLM in its context -- nothing else is legal).
      4. Has a LIMIT if it looks like a row-level (non-aggregate) query;
         auto-appends a safety LIMIT if missing.
    """
    try:
        statements = sqlglot.parse(sql, read="snowflake")
    except Exception as e:
        return False, f"SQL failed to parse: {e}", sql

    if len(statements) != 1:
        return False, "Exactly one statement is allowed per query.", sql

    stmt = statements[0]

    if isinstance(stmt, FORBIDDEN_STATEMENT_TYPES) or not isinstance(stmt, exp.Select):
        return False, "Only single SELECT statements are permitted.", sql

    # Extract every table reference in the query (handles joins, subqueries, CTEs)
    referenced_tables = {
        t.name.upper() for t in stmt.find_all(exp.Table)
    }
    allowed_upper = {t.upper() for t in allowed_tables}
    disallowed = referenced_tables - allowed_upper
    if disallowed:
        return False, f"Query references table(s) outside allowed set: {disallowed}", sql

    # Safety net: if there's no aggregation and no LIMIT, append one.
    has_aggregate = any(stmt.find_all((exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max)))
    has_limit = stmt.args.get("limit") is not None
    if not has_aggregate and not has_limit:
        stmt = stmt.limit(DEFAULT_ROW_LIMIT)
        sql = stmt.sql(dialect="snowflake")

    return True, "ok", sql
