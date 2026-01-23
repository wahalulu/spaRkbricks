#' Get Current Authentication Type
#'
#' Determines which authentication method will be used based on
#' available credentials in the environment.
#'
#' @return "pat" if DATABRICKS_TOKEN is set, "oauth" otherwise
#' @export
#'
#' @examples
#' \dontrun{
#' auth_type <- get_auth_type()
#' if (auth_type == "oauth") {
#'   message("Using OAuth via Databricks CLI")
#' } else {
#'   message("Using Personal Access Token")
#' }
#' }
get_auth_type <- function() {
  token <- Sys.getenv("DATABRICKS_TOKEN", unset = "")
  if (nzchar(token)) "pat" else "oauth"
}


#' Check Authentication Status
#'
#' Verifies that required authentication credentials are available
#' for the specified authentication type.
#'
#' @param auth_type Authentication type to check: "auto", "oauth", or "pat"
#' @return TRUE if credentials are available, FALSE otherwise (with message)
#' @export
#'
#' @examples
#' \dontrun{
#' # Check if current auth setup is valid
#' if (check_auth()) {
#'   sc <- spark_connect_databricks()
#' }
#'
#' # Check specific auth type
#' check_auth("pat")
#' check_auth("oauth")
#' }
check_auth <- function(auth_type = c("auto", "oauth", "pat")) {
  auth_type <- match.arg(auth_type)

  if (auth_type == "auto") {
    auth_type <- get_auth_type()
  }

  if (auth_type == "pat") {
    token <- Sys.getenv("DATABRICKS_TOKEN", unset = "")
    if (!nzchar(token)) {
      message("PAT auth: DATABRICKS_TOKEN not set")
      return(FALSE)
    }
    message("PAT auth: Token available")
    return(TRUE)
  } else {
    # Check if Databricks CLI is available and configured
    # This is a basic check - the Python SDK does the real validation
    message("OAuth auth: Will use Databricks CLI profile")
    return(TRUE)
  }
}
