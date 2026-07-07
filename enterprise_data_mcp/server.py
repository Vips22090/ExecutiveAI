"""
enterprise_data_mcp/server.py

An MCP server that exposes Snowflake data as tools for the executive_ai agent.

Security design:
- Authenticates via RSA key-pair (no password ever stored/typed).
- Connects using a dedicated, least-privilege Snowflake role (read-only).
- Only allows SELECT statements -- anything else is rejected before it
  reaches Snowflake.
- Every query is capped with a row limit so a broad question can't pull
  back an enormous, costly result set.

Environment variables required (put these in a .env file that is
git-ignored, NEVER commit them):
    SNOWFLAKE_ACCOUNT              e.g. xy12345.us-east-1
    SNOWFLAKE_USER                 e.g. MCP_SERVICE_USER
    SNOWFLAKE_ROLE                 e.g. MCP_READONLY_ROLE
    SNOWFLAKE_WAREHOUSE            e.g. MCP_WAREHOUSE
    SNOWFLAKE_DATABASE             e.g. EXECUTIVE_AI_DB
    SNOWFLAKE_SCHEMA               e.g. PUBLIC
    SNOWFLAKE_PRIVATE_KEY_PATH     full path to your .p8 private key file
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE   (optional, only if key is encrypted)
"""
import os
import re
import logging
import datetime
import decimal
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import snowflake.connector
from mcp.server.fastmcp import FastMCP

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enterprise_data_mcp")

MAX_ROWS = 500  # hard cap on any query result, regardless of what's asked

mcp = FastMCP("enterprise-data-mcp")


def _load_private_key():
    key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]
    passphrase = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    with open(key_path, "rb") as f:
        p_key = serialization.load_pem_private_key(
            f.read(),
            password=passphrase.encode() if passphrase else None,
        )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_connection():
    """Opens a fresh Snowflake connection using key-pair auth.
    No password is ever read, stored, or transmitted by this server.
    """
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_load_private_key(),
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )


def _is_safe_select(sql: str) -> bool:
    """Guardrail: only a single, plain SELECT statement is allowed.
    Rejects anything with a semicolon (multiple statements), or any
    non-SELECT keyword like INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/GRANT.
    """
    cleaned = sql.strip().rstrip(";").strip()
    if ";" in cleaned:
        return False
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        return False
    forbidden = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|GRANT|REVOKE|MERGE|TRUNCATE|CALL)\b"
    if re.search(forbidden, cleaned, re.IGNORECASE):
        return False
    return True


def _make_serializable(value):
    """Convert Snowflake-native types to JSON-safe Python types.
    Snowflake cursors can return datetime.date, datetime.datetime,
    and decimal.Decimal -- none of which are JSON serializable by default.
    """
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    return value


@mcp.tool()
def list_tables() -> dict:
    """Lists tables available in the configured Snowflake database/schema.

    Use this first if you don't know what data exists before writing a query.

    Returns:
        A dict with a list of table names and row counts.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT table_name, row_count FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY table_name",
            (os.environ["SNOWFLAKE_SCHEMA"],),
        )
        rows = cur.fetchall()
        return {"tables": [{"table_name": r[0], "row_count": r[1]} for r in rows]}
    except Exception as e:
        logger.error(f"list_tables failed: {e}")
        return {"error": "Could not list tables. Check connection and permissions."}
    finally:
        conn.close()


@mcp.tool()
def describe_table(table_name: str) -> dict:
    """Describes the columns of a specific table.

    Args:
        table_name: The name of the table to describe (from list_tables).

    Returns:
        A dict listing column names and data types.
    """
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (os.environ["SNOWFLAKE_SCHEMA"], table_name.upper()),
        )
        rows = cur.fetchall()
        if not rows:
            return {"error": f"No columns found for table '{table_name}'. Check the name via list_tables."}
        return {"table_name": table_name, "columns": [{"name": r[0], "type": r[1]} for r in rows]}
    except Exception as e:
        logger.error(f"describe_table failed: {e}")
        return {"error": "Could not describe table. Check connection and permissions."}
    finally:
        conn.close()


@mcp.tool()
def run_query(sql: str) -> dict:
    """Runs a read-only SQL query against Snowflake and returns the results.

    Only SELECT statements are permitted -- any attempt to modify data
    (INSERT/UPDATE/DELETE/DROP/etc.) is rejected before reaching Snowflake.
    Results are capped at 500 rows.

    Args:
        sql: A single SELECT statement, e.g.
             "SELECT month, revenue FROM company_metrics ORDER BY month DESC LIMIT 12"

    Returns:
        A dict with the column names and resulting rows, or an error message.
    """
    if not _is_safe_select(sql):
        return {"error": "Only single SELECT statements are allowed. Query rejected."}

    # Enforce a hard row cap regardless of what the query itself requests
    capped_sql = sql.strip().rstrip(";")
    if "LIMIT" not in capped_sql.upper():
        capped_sql = f"{capped_sql} LIMIT {MAX_ROWS}"

    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute(capped_sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchmany(MAX_ROWS)
        return {
            "columns": columns,
            "row_count": len(rows),
            "rows": [
                {col: _make_serializable(val) for col, val in zip(columns, row)}
                for row in rows
            ],
        }
    except Exception as e:
        logger.error(f"run_query failed: {e}")
        return {"error": f"Query failed: {str(e)}"}
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()
