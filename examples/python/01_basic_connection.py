"""Basic connection example for sparkbricks.

This example demonstrates the simplest way to connect to Databricks.
Auth is auto-detected: PAT if DATABRICKS_TOKEN is set, else OAuth.

Prerequisites:
    1. Set environment variables in .env file:
       - DATABRICKS_HOST
       - DATABRICKS_CLUSTER_ID
       - DATABRICKS_TOKEN (optional, for PAT auth)

    2. For OAuth: Run `databricks auth login --host <your-host>` first

Usage:
    uv run python examples/python/01_basic_connection.py
"""

from sparkbricks import get_spark, close_spark, cluster_status, sql

# Check cluster status before connecting
print("Checking cluster status...")
status = cluster_status()
print(f"Cluster status: {status}")

# Connect to Databricks (auto-starts cluster if needed)
print("\nConnecting to Databricks...")
spark = get_spark()

if spark:
    # Run a simple query
    print("\nRunning test query...")
    df = sql("SELECT 1 as test_value, current_timestamp() as query_time", show=True)

    # Show Spark version
    print(f"\nSpark version: {spark.version}")

    # Clean up
    print("\nDisconnecting...")
    close_spark()
else:
    print("Failed to connect. Check your credentials and cluster status.")
