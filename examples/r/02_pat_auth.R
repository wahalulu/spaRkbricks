# PAT authentication example for spaRkbricks
#
# This example demonstrates using Personal Access Token (PAT) authentication
# explicitly, regardless of OAuth configuration.
#
# Prerequisites:
#   1. Create a PAT in Databricks workspace:
#      User Settings > Developer > Access Tokens > Generate new token
#
#   2. Set in .env file or environment:
#      - DATABRICKS_HOST
#      - DATABRICKS_CLUSTER_ID
#      - SPARKBRICKS_PYTHON_ENV
#      - DATABRICKS_TOKEN

library(spaRkbricks)

# Check what auth type would be used
detected_auth <- get_auth_type()
message(sprintf("Detected auth type: %s", detected_auth))

# Check if token is available
token <- Sys.getenv("DATABRICKS_TOKEN", unset = "")
if (!nzchar(token)) {
  stop("DATABRICKS_TOKEN not set. Set it in .env or Sys.setenv()")
}

message(sprintf("Token found (first 10 chars): %s...", substr(token, 1, 10)))

# Check auth status
check_auth("pat")

# Connect explicitly with PAT auth
message("\nConnecting with PAT authentication...")
sc <- spark_connect_databricks(auth_type = "pat")

# Run a query
message("\nRunning test query...")
result <- sparklyr::sdf_sql(sc, "SELECT 'PAT auth successful!' as message")
print(result)

# Clean up
spark_disconnect_databricks(sc)

message("Done!")
