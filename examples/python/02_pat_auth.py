"""PAT authentication example for sparkbricks.

This example demonstrates using Personal Access Token (PAT) authentication
explicitly, regardless of OAuth configuration.

Prerequisites:
    1. Create a PAT in Databricks workspace:
       User Settings > Developer > Access Tokens > Generate new token

    2. Set in .env file or environment:
       - DATABRICKS_HOST
       - DATABRICKS_CLUSTER_ID
       - DATABRICKS_TOKEN

Usage:
    export DATABRICKS_TOKEN=dapi...
    uv run python examples/python/02_pat_auth.py
"""

import os
from sparkbricks import get_spark, close_spark, get_auth_type, sql

# Check what auth type would be used
detected_auth = get_auth_type()
print(f"Detected auth type: {detected_auth}")

# Check if token is available
token = os.environ.get("DATABRICKS_TOKEN")
if not token:
    print("ERROR: DATABRICKS_TOKEN not set.")
    print("Set it in .env or export DATABRICKS_TOKEN=dapi...")
    exit(1)

print(f"Token found (first 10 chars): {token[:10]}...")

# Connect explicitly with PAT auth
print("\nConnecting with PAT authentication...")
spark = get_spark(auth_type="pat")

if spark:
    # Run a query
    print("\nRunning test query...")
    sql("SELECT 'PAT auth successful!' as message", show=True)

    # Clean up
    close_spark()
else:
    print("Failed to connect with PAT authentication.")
