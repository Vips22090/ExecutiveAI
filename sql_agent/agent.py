"""
sql_agent
---------
Generates and safely executes SQL against Snowflake (via your MCP server),
using ONLY the static knowledge files as context -- never live schema
discovery, never metadata probing at request time.

Flow per question:
  1. get_context(question)  -> router match + minimal schema/kpi/join context
                                (pure code, no LLM, no DB hit)
  2. LLM writes SQL using ONLY what get_context returned
  3. run_sql(sql, context_id) -> static validation, then execution
                                  (validation is pure code; only
                                  execution touches Snowflake)

NOTE ON MRR (see conversation): kpis.json currently defines MRR as a
raw SUM(AMOUNT) over all SUBSCRIPTIONS events. This is only correct if
Cancel/Downgrade events carry negative or offsetting amounts. Confirm
this against your actual data before trusting MRR output --
`_kpi_filter_hint()` below has a TODO marking where a filter
(e.g. WHERE EVENT != 'Cancel') would need to go if that's not the case.
"""

import uuid
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from . import context_assembler
from .validator import validate_sql

# In-memory cache mapping context_id -> allowed_tables.
# This exists so the model CANNOT simply claim a different allowed_tables
# set when calling run_sql -- it must reference a context_id we generated,
# and we look up the real allowed tables ourselves rather than trusting
# whatever the model passes back.
# For multi-user / multi-session production use, replace this with
# ADK session state (tool_context.state) keyed by session id, not a
# bare process-global dict.
_CONTEXT_CACHE: dict[str, dict] = {}


def _match_intent(question: str) -> tuple[list[str], Optional[str]]:
    """
    Lightweight keyword-overlap router against examples.json.
    Swap this out for an embedding-similarity search once you have
    enough real traffic to justify it -- for now this is a zero-cost,
    zero-LLM-call first pass.
    """
    question_l = question.lower()
    best_score, best = 0, None

    for ex in context_assembler.get_examples():
        for phrasing in ex["questions"]:
            phrasing_words = set(phrasing.lower().split())
            question_words = set(question_l.split())
            overlap = len(phrasing_words & question_words)
            if overlap > best_score:
                best_score, best = overlap, ex

    if best is None or best_score == 0:
        # No confident match -- fall back to letting the LLM pick from
        # ALL tables' business_questions in schema.json. Still no live
        # DB access; just a wider (but still static) net.
        return context_assembler.all_table_names(), None

    return best["tables"], best.get("kpi")


def get_context(question: str) -> dict:
    """
    TOOL: Given the CEO's question, return the minimal schema/KPI/join
    context needed to write SQL, plus a context_id to pass to run_sql.
    """
    tables, kpi_name = _match_intent(question)
    ctx = context_assembler.assemble_context(tables, kpi_name)

    context_id = str(uuid.uuid4())
    _CONTEXT_CACHE[context_id] = {"allowed_tables": ctx["allowed_tables"]}

    return {
        "context_id": context_id,
        "tables": ctx["tables"],
        "joins": ctx["joins"],
        "kpi": ctx["kpi"],
    }


def run_sql(sql: str, context_id: str) -> dict:
    """
    TOOL: Validate then execute SQL. Only tables present in the
    context identified by context_id are permitted, regardless of
    what the model claims -- context_id is our source of truth, not
    an argument the model can spoof.
    """
    cached = _CONTEXT_CACHE.get(context_id)
    if cached is None:
        return {"error": "Unknown or expired context_id. Call get_context first.", "rows": None}

    allowed_tables = cached["allowed_tables"]
    is_valid, reason, safe_sql = validate_sql(sql, allowed_tables)
    if not is_valid:
        return {"error": f"Query rejected: {reason}", "sql": sql, "rows": None}

    try:
        rows, columns = _execute_on_snowflake(safe_sql)
    except Exception as e:
        # Bounded retry logic (max 1 retry) belongs in the calling agent's
        # instruction, not here -- this function should stay a dumb,
        # honest executor.
        return {"error": f"Execution failed: {e}", "sql": safe_sql, "rows": None}

    return {
        "error": None,
        "sql": safe_sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


def _execute_on_snowflake(sql: str) -> tuple[list[dict], list[str]]:
    """
    Executes via enterprise_data_mcp's run_query, which independently
    re-validates (regex-based safe-SELECT check) and enforces its own
    hard row cap (MAX_ROWS) at fetch time -- a second, independent
    layer on top of this module's sqlglot-based validation.

    Imported lazily so importing sql_agent doesn't require Snowflake
    credentials to be configured (useful for the dry import test).
    """
    from enterprise_data_mcp.server import run_query as mcp_run_query

    result = mcp_run_query(sql)
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["rows"], result["columns"]


get_context_tool = FunctionTool(func=get_context)
run_sql_tool = FunctionTool(func=run_sql)

root_agent = Agent(
    model="gemini-2.0-flash",
    name="sql_agent",
    description=(
        "Generates and safely executes Snowflake SQL using only the "
        "provided static schema/KPI knowledge -- never live schema discovery."
    ),
    instruction=(
        "You translate business questions into Snowflake SQL.\n\n"
        "WORKFLOW (follow exactly, in order):\n"
        "1. Call get_context(question) FIRST. It returns table schemas, "
        "a matched KPI definition (if any), join conditions, and a context_id.\n"
        "2. Write exactly one SELECT statement using ONLY the tables/columns "
        "given in that context. Never reference a table not present there. "
        "If a KPI definition is provided, use its exact aggregation, columns, "
        "and grouping -- do not invent your own formula.\n"
        "3. Call run_sql(sql, context_id) using the context_id from step 1.\n"
        "4. If run_sql returns an error, read the error message, fix the SQL "
        "accordingly, and call run_sql ONE more time. Do not retry more than once.\n"
        "5. Return the final result as-is (columns, rows, row_count) -- do not "
        "add commentary here; that belongs to the coordinator/insight agent.\n\n"
        "RULES:\n"
        "- Never write INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/MERGE.\n"
        "- Never reference a table or column not present in get_context's output.\n"
        "- If get_context returns no matching KPI, reason carefully about which "
        "columns answer the question using only the schema provided.\n"
    ),
    tools=[get_context_tool, run_sql_tool],
)
