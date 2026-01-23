# Basic connection example for spaRkbricks
#
# This example demonstrates the simplest way to connect to Databricks from R.
# Auth is auto-detected: PAT if DATABRICKS_TOKEN is set, else OAuth.
#
# Prerequisites:
#   1. Install the package:
#      install.packages("path/to/r/spaRkbricks", repos = NULL, type = "source")
#
#   2. Set environment variables in .env file:
#      - DATABRICKS_HOST
#      - DATABRICKS_CLUSTER_ID
#      - SPARKBRICKS_PYTHON_ENV (path to Python venv)
#      - DATABRICKS_TOKEN (optional, for PAT auth)
#
#   3. For OAuth: Run `databricks auth login --host <your-host>` first
#
# Note: Do NOT run this from Git Bash on Windows (causes segfaults).
#       Use PowerShell, RStudio, or Windows Command Prompt.

library(spaRkbricks)

# Check what auth type will be used
auth_type <- get_auth_type()
message(sprintf("Detected auth type: %s", auth_type))

# Check authentication status
check_auth()

# Check cluster status
message("\nChecking cluster status...")
status <- cluster_status()
message(sprintf("Cluster status: %s", status))

# Connect to Databricks (auto-starts cluster if needed)
message("\nConnecting to Databricks...")
sc <- spark_connect_databricks()

# Run a simple query
message("\nRunning test query...")
result <- sparklyr::sdf_sql(sc, "SELECT 1 as test_value, current_timestamp() as query_time")
print(result)

# If you have dplyr installed, you can use it
if (requireNamespace("dplyr", quietly = TRUE)) {
  library(dplyr)
  message("\nCollecting result with dplyr...")
  collected <- result |> collect()
  print(collected)
}

# Clean up - IMPORTANT: Always disconnect properly!
message("\nDisconnecting...")
spark_disconnect_databricks(sc)

message("Done!")
