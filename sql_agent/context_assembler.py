"""
Context Assembler
------------------
Pure-code (no LLM) step that builds the minimal context payload
sql_agent needs to generate SQL for a given question.

It never talks to Snowflake. It only reads the static knowledge
files (schema.json, kpis.json, relationships.json) that live in
your `knowledge/` folder.
"""

import json
from pathlib import Path
from typing import Optional

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def _load(name: str) -> dict:
    with open(KNOWLEDGE_DIR / name, "r") as f:
        return json.load(f)


# Loaded once at import time and cached in memory for the process lifetime.
# Regenerate these files on a schedule / on deploy, not at request time.
_SCHEMA = _load("schema.json")
_KPIS = _load("kpis.json")
_RELATIONSHIPS = _load("relationships.json")
_EXAMPLES = _load("examples.json")


def assemble_context(tables: list[str], kpi_name: Optional[str] = None) -> dict:
    """
    Build a minimal context dict containing only what's needed
    to generate SQL for the given tables (+ optional matched KPI).

    Keeping this scoped to `tables` (rather than dumping the whole
    schema) is what keeps token cost flat as your DB grows.
    """
    all_tables = _SCHEMA.get("tables", {})
    missing = [t for t in tables if t not in all_tables]
    if missing:
        raise ValueError(f"Unknown table(s) requested: {missing}")

    schema_ctx = {t: all_tables[t] for t in tables}

    joins = [
        r for r in _RELATIONSHIPS.get("relationships", [])
        if r["from_table"] in tables and r["to_table"] in tables
    ]

    kpi_ctx = None
    if kpi_name:
        kpi_ctx = _KPIS.get("kpis", {}).get(kpi_name)
        if kpi_ctx is None:
            # Not necessarily fatal -- some intents (e.g. "Executive Business
            # Overview") map to composite KPIs that don't exist as a single
            # entry. Caller should treat kpi_ctx=None as "no template match,
            # let the LLM reason freely within the given schema/joins".
            pass

    return {
        "tables": schema_ctx,
        "joins": joins,
        "kpi": kpi_ctx,
        "allowed_tables": list(tables),  # used later for SQL validation
    }


def all_table_names() -> list[str]:
    return list(_SCHEMA.get("tables", {}).keys())


def get_examples() -> list[dict]:
    return _EXAMPLES.get("examples", [])
