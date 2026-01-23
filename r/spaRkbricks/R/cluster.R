#' Get Cluster Status
#'
#' Returns the current status of a Databricks cluster.
#' Supports both OAuth and PAT authentication.
#'
#' @param cluster_id Databricks cluster ID. If NULL, reads from DATABRICKS_CLUSTER_ID env var.
#' @param token Personal Access Token. If NULL, reads from DATABRICKS_TOKEN env var.
#' @param auth_type Authentication type: "auto", "oauth", or "pat"
#' @param envname Path to the Python virtual environment (default: auto-detect)
#'
#' @return A string indicating cluster status (e.g., "RUNNING", "TERMINATED", "PENDING")
#' @export
#'
#' @examples
#' \dontrun{
#' status <- cluster_status()
#' print(status)  # "RUNNING" or "TERMINATED" etc.
#'
#' # With PAT auth
#' status <- cluster_status(token = "dapi...")
#' }
cluster_status <- function(
    cluster_id = NULL,
    token = NULL,
    auth_type = c("auto", "oauth", "pat"),
    envname = NULL
) {
  auth_type <- match.arg(auth_type)
  .init_python(envname)

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

  sparkbricks <- reticulate::import("sparkbricks")
  status <- sparkbricks$cluster_status(
    cluster_id = cluster_id,
    token = effective_token,
    auth_type = auth_type
  )

  return(status)
}


#' Start Databricks Cluster
#'
#' Starts a Databricks cluster if it's not already running.
#' Supports both OAuth and PAT authentication.
#'
#' @param cluster_id Databricks cluster ID. If NULL, reads from DATABRICKS_CLUSTER_ID env var.
#' @param token Personal Access Token. If NULL, reads from DATABRICKS_TOKEN env var.
#' @param auth_type Authentication type: "auto", "oauth", or "pat"
#' @param wait If TRUE, wait for the cluster to reach RUNNING state
#' @param envname Path to the Python virtual environment (default: auto-detect)
#'
#' @return TRUE if cluster started successfully
#' @export
#'
#' @examples
#' \dontrun{
#' # Start and wait for cluster
#' start_cluster(wait = TRUE)
#'
#' # Start with PAT auth
#' start_cluster(token = "dapi...", wait = TRUE)
#' }
start_cluster <- function(
    cluster_id = NULL,
    token = NULL,
    auth_type = c("auto", "oauth", "pat"),
    wait = TRUE,
    envname = NULL
) {
  auth_type <- match.arg(auth_type)
  .init_python(envname)

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

  sparkbricks <- reticulate::import("sparkbricks")

  message(sprintf("Starting cluster %s...", cluster_id))
  result <- sparkbricks$start_cluster(
    cluster_id = cluster_id,
    token = effective_token,
    auth_type = auth_type,
    wait = wait
  )

  if (wait && result) {
    message(sprintf("Cluster %s is now RUNNING", cluster_id))
  } else if (!wait) {
    message(sprintf("Cluster %s start initiated", cluster_id))
  }

  return(result)
}


#' Stop Databricks Cluster
#'
#' Stops a running Databricks cluster.
#' Supports both OAuth and PAT authentication.
#'
#' @param cluster_id Databricks cluster ID. If NULL, reads from DATABRICKS_CLUSTER_ID env var.
#' @param token Personal Access Token. If NULL, reads from DATABRICKS_TOKEN env var.
#' @param auth_type Authentication type: "auto", "oauth", or "pat"
#' @param envname Path to the Python virtual environment (default: auto-detect)
#'
#' @return TRUE if stop was initiated successfully
#' @export
#'
#' @examples
#' \dontrun{
#' stop_cluster()
#'
#' # With PAT auth
#' stop_cluster(token = "dapi...")
#' }
stop_cluster <- function(
    cluster_id = NULL,
    token = NULL,
    auth_type = c("auto", "oauth", "pat"),
    envname = NULL
) {
  auth_type <- match.arg(auth_type)
  .init_python(envname)

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

  sparkbricks <- reticulate::import("sparkbricks")

  message(sprintf("Stopping cluster %s...", cluster_id))
  sparkbricks$stop_cluster(
    cluster_id = cluster_id,
    token = effective_token,
    auth_type = auth_type
  )
  message(sprintf("Cluster %s stop initiated", cluster_id))

  return(TRUE)
}


#' Ensure Cluster is Running
#'
#' Ensures a Databricks cluster is running, starting it if necessary.
#' This is a convenience function that combines status check and start.
#' Supports both OAuth and PAT authentication.
#'
#' @param cluster_id Databricks cluster ID. If NULL, reads from DATABRICKS_CLUSTER_ID env var.
#' @param token Personal Access Token. If NULL, reads from DATABRICKS_TOKEN env var.
#' @param auth_type Authentication type: "auto", "oauth", or "pat"
#' @param envname Path to the Python virtual environment (default: auto-detect)
#'
#' @return TRUE if cluster is running
#' @export
#'
#' @examples
#' \dontrun{
#' ensure_cluster_running()
#' # Now safe to connect
#' sc <- spark_connect_databricks()
#' }
ensure_cluster_running <- function(
    cluster_id = NULL,
    token = NULL,
    auth_type = c("auto", "oauth", "pat"),
    envname = NULL
) {
  auth_type <- match.arg(auth_type)
  .init_python(envname)

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

  sparkbricks <- reticulate::import("sparkbricks")

  status <- sparkbricks$cluster_status(
    cluster_id = cluster_id,
    token = effective_token,
    auth_type = auth_type
  )

  if (status == "RUNNING") {
    message(sprintf("Cluster %s is already running", cluster_id))
    return(TRUE)
  }

  message(sprintf("Cluster %s status: %s. Starting...", cluster_id, status))
  sparkbricks$start_cluster(
    cluster_id = cluster_id,
    token = effective_token,
    auth_type = auth_type,
    wait = TRUE
  )
  message(sprintf("Cluster %s is now running", cluster_id))

  return(TRUE)
}
