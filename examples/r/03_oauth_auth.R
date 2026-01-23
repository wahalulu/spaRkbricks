# OAuth authentication example for spaRkbricks
#
# This example demonstrates using OAuth (via Databricks CLI) authentication
# explicitly. OAuth provides automatic token refresh for long-running sessions.
#
# Prerequisites:
#   1. Install Databricks CLI:
#      curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
#
#   2. Login with OAuth:
#      databricks auth login --host https://your-workspace.azuredatabricks.net
#
#   3. Set in .env file:
#      - DATABRICKS_HOST
#      - DATABRICKS_CLUSTER_ID
#      - SPARKBRICKS_PYTHON_ENV
#
#   4. Make sure DATABRICKS_TOKEN is NOT set:
#      Sys.unsetenv("DATABRICKS_TOKEN")
#
# Note: Do NOT run this from Git Bash on Windows (causes segfaults).
#       Use PowerShell, RStudio, or Windows Command Prompt.

library(spaRkbricks)

# Check what auth type would be used
detected_auth <- get_auth_type()
message(sprintf("Detected auth type: %s", detected_auth))

# Warn if PAT token is set
if (nzchar(Sys.getenv("DATABRICKS_TOKEN", unset = ""))) {
  message("WARNING: DATABRICKS_TOKEN is set. Will use PAT instead of OAuth.")
  message("Run: Sys.unsetenv('DATABRICKS_TOKEN')")
  message("Then re-run this script.")
  stop("Unset DATABRICKS_TOKEN to use OAuth")
}

message("No DATABRICKS_TOKEN found - will use OAuth via Databricks CLI")

# Check auth status
check_auth("oauth")

# Connect explicitly with OAuth
message("\nConnecting with OAuth authentication...")
message("Note: This requires 'databricks auth login' to have been run")

sc <- spark_connect_databricks(auth_type = "oauth", profile = "DEFAULT")

# Run a query
message("\nRunning test query...")
result <- sparklyr::sdf_sql(sc, "SELECT 'OAuth auth successful!' as message")
print(result)

message("\nOAuth benefits:")
message("- Automatic token refresh (no manual renewal)")
message("- Works with long-running sessions")
message("- No token to manage or rotate")

# Clean up
spark_disconnect_databricks(sc)

message("Done!")
