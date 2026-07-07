"""
Run this once to test that the Snowflake connection works, using your
.env file and key-pair auth. If this succeeds, the harder part is done --
the full MCP server (server.py) uses the exact same connection logic.
"""
import os
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
import snowflake.connector

load_dotenv()

print("Loading private key from:", os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])

with open(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"], "rb") as f:
    p_key = serialization.load_pem_private_key(f.read(), password=None)

private_key_bytes = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

print("Connecting to Snowflake as:", os.environ["SNOWFLAKE_USER"])

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key=private_key_bytes,
    role=os.environ["SNOWFLAKE_ROLE"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=os.environ["SNOWFLAKE_DATABASE"],
    schema=os.environ["SNOWFLAKE_SCHEMA"],
)

print("Connected successfully!")

cur = conn.cursor()
cur.execute("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();")
row = cur.fetchone()
print("\nConnected as:")
print("  User:     ", row[0])
print("  Role:     ", row[1])
print("  Warehouse:", row[2])
print("  Database: ", row[3])
print("  Schema:   ", row[4])

print("\nTables visible to this role:")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name",
            (os.environ["SNOWFLAKE_SCHEMA"],))
for r in cur.fetchall():
    print("  -", r[0])

conn.close()
print("\nDone. Connection test successful.")
