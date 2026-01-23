"""OAuth authentication example for sparkbricks.

This example demonstrates using OAuth (via Databricks CLI) authentication
explicitly. OAuth provides automatic token refresh for long-running sessions.

Prerequisites:
    1. Install Databricks CLI:
       curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

    2. Login with OAuth:
       databricks auth login --host https://your-workspace.azuredatabricks.net

    3. Set in .env file:
       - DATABRICKS_HOST
       - DATABRICKS_CLUSTER_ID

    4. Make sure DATABRICKS_TOKEN is NOT set (unset it if needed)

Usage:
    unset DATABRICKS_TOKEN
    uv run python examples/python/03_oauth_auth.py
"""

import os
from sparkbricks import get_spark, close_spark, get_auth_type, sql

# Check what auth type would be used
detected_auth = get_auth_type()
print(f"Detected auth type: {detected_auth}")

# Warn if PAT token is set
if os.environ.get("DATABRICKS_TOKEN"):
    print("WARNING: DATABRICKS_TOKEN is set. Will use PAT instead of OAuth.")
    print("Run: unset DATABRICKS_TOKEN")
    print("Then re-run this script.")
    exit(1)

print("No DATABRICKS_TOKEN found - will use OAuth via Databricks CLI")

# Connect explicitly with OAuth
print("\nConnecting with OAuth authentication...")
print("Note: This requires 'databricks auth login' to have been run")

spark = get_spark(auth_type="oauth", profile="DEFAULT")

if spark:
    # Run a query
    print("\nRunning test query...")
    sql("SELECT 'OAuth auth successful!' as message", show=True)

    print("\nOAuth benefits:")
    print("- Automatic token refresh (no manual renewal)")
    print("- Works with long-running sessions")
    print("- No token to manage or rotate")

    # Clean up
    close_spark()
else:
    print("Failed to connect with OAuth authentication.")
    print("\nTroubleshooting:")
    print("1. Run: databricks auth login --host <your-host>")
    print("2. Check ~/.databrickscfg exists and has DEFAULT profile")
    print("3. Ensure Databricks CLI is in PATH")
