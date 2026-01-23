#' Connect to Databricks Spark Cluster
#'
#' Establishes a connection to a Databricks Spark cluster using either
#' OAuth (via Databricks CLI) or Personal Access Token (PAT) authentication.
#'
#' @param host Databricks workspace URL. If NULL, reads from DATABRICKS_HOST env var.
#' @param cluster_id Databricks cluster ID. If NULL, reads from DATABRICKS_CLUSTER_ID env var.
#' @param token Personal Access Token. If NULL, reads from DATABRICKS_TOKEN env var.
#'              If provided (or env var set), uses PAT auth. Otherwise uses OAuth.
#' @param profile Databricks CLI profile name (for OAuth auth, default: "DEFAULT")
#' @param auth_type Authentication type: "auto" (default), "oauth", or "pat".
#'                  "auto" uses PAT if token is available, otherwise OAuth.
#' @param auto_start If TRUE, automatically start the cluster if not running
#' @param envname Path to Python virtual environment (default: auto-detect)
#'
#' @return A sparklyr connection object
#' @export
#'
#' @examples
#' \dontrun{
#' # Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
#' sc <- spark_connect_databricks()
#'
#' # Explicit PAT auth
#' sc <- spark_connect_databricks(token = "dapi...")
#'
#' # Explicit OAuth with specific profile
#' sc <- spark_connect_databricks(auth_type = "oauth", profile = "work")
#'
#' # Use with dplyr
#' library(dplyr)
#' tbl(sc, "catalog.schema.table") |> filter(x > 10) |> collect()
#'
#' # Disconnect properly
#' spark_disconnect_databricks(sc)
#' }
spark_connect_databricks <- function(
    host = NULL,
    cluster_id = NULL,
    token = NULL,
    profile = "DEFAULT",
    auth_type = c("auto", "oauth", "pat"),
    auto_start = TRUE,
    envname = NULL
) {
  auth_type <- match.arg(auth_type)

  # Initialize Python environment using centralized init
  .init_python(envname)

  # Import sparkbricks
  sparkbricks <- reticulate::import("sparkbricks")

  # Get connection parameters from env vars if not provided
  if (is.null(host)) {
    host <- Sys.getenv("DATABRICKS_HOST", unset = NA)
    if (is.na(host)) {
      stop("DATABRICKS_HOST environment variable not set. Set it or pass host parameter.")
    }
  }

  if (is.null(cluster_id)) {
    cluster_id <- Sys.getenv("DATABRICKS_CLUSTER_ID", unset = NA)
    if (is.na(cluster_id)) {
      stop("DATABRICKS_CLUSTER_ID environment variable not set. Set it or pass cluster_id parameter.")
    }
  }

  # Resolve token
  effective_token <- token
  if (is.null(effective_token)) {
    env_token <- Sys.getenv("DATABRICKS_TOKEN", unset = "")
    if (nzchar(env_token)) {
      effective_token <- env_token
    }
  }

  # Determine effective auth type
  if (auth_type == "auto") {
    effective_auth <- if (!is.null(effective_token)) "pat" else "oauth"
  } else {
    effective_auth <- auth_type
  }

  # Validate PAT auth has token
  if (effective_auth == "pat" && is.null(effective_token)) {
    stop("PAT auth requires token parameter or DATABRICKS_TOKEN env var")
  }

  message(sprintf("Connecting to %s (auth: %s)...", host, effective_auth))

  # Start cluster if requested and needed
  if (auto_start) {
    status <- sparkbricks$cluster_status(
      cluster_id = cluster_id,
      host = host,
      token = effective_token,
      profile = profile,
      auth_type = effective_auth
    )
    if (status != "RUNNING") {
      message(sprintf("Cluster status: %s. Starting...", status))
      sparkbricks$start_cluster(
        cluster_id = cluster_id,
        host = host,
        token = effective_token,
        profile = profile,
        auth_type = effective_auth,
        wait = TRUE
      )
    }
  }

  # Create Python Spark session
  spark <- sparkbricks$get_spark(
    host = host,
    cluster_id = cluster_id,
    token = effective_token,
    profile = profile,
    auth_type = effective_auth
  )

  # Set up environment for sparklyr
  if (effective_auth == "pat") {
    # PAT auth - set token directly
    Sys.setenv(DATABRICKS_TOKEN = effective_token)
    Sys.setenv(DATABRICKS_HOST = host)
    Sys.setenv(DATABRICKS_CLUSTER_ID = cluster_id)
  } else {
    # OAuth - extract token from SDK for sparklyr
    py_code <- sprintf("
import os
from databricks.sdk.core import Config

config = Config(
    host='%s',
    cluster_id='%s',
    auth_type='databricks-cli',
    profile='%s'
)

headers = config.authenticate()
token = headers.get('Authorization', '').replace('Bearer ', '')

os.environ['DATABRICKS_TOKEN'] = token
os.environ['DATABRICKS_HOST'] = '%s'
os.environ['DATABRICKS_CLUSTER_ID'] = '%s'
", host, cluster_id, profile, host, cluster_id)

    reticulate::py_run_string(py_code)
  }

  # Connect via sparklyr
  sc <- sparklyr::spark_connect(
    method = "databricks_connect",
    cluster_id = cluster_id
  )

  message(sprintf("Connected to Databricks cluster %s", cluster_id))

  return(sc)
}


#' Disconnect from Databricks Spark Cluster
#'
#' Properly disconnects from the Databricks Spark cluster, closing both the
#' sparklyr connection and the underlying Python DatabricksSession.
#'
#' This function is important because without it, the Python session would
#' remain open (orphaned) after the R session disconnects.
#'
#' @param sc A sparklyr connection object returned by spark_connect_databricks()
#'
#' @return NULL (invisibly)
#' @export
#'
#' @examples
#' \dontrun{
#' sc <- spark_connect_databricks()
#' # ... do work ...
#' spark_disconnect_databricks(sc)
#' }
spark_disconnect_databricks <- function(sc) {
  # Close sparklyr connection first
  sparklyr::spark_disconnect(sc)

  # Close the Python session to avoid orphaned sessions
  tryCatch({
    sparkbricks <- reticulate::import("sparkbricks")
    sparkbricks$close_spark()
    message("Disconnected from Databricks (both R and Python sessions closed)")
  }, error = function(e) {
    message("Note: Could not close Python session. It may already be closed.")
  })

  invisible(NULL)
}
