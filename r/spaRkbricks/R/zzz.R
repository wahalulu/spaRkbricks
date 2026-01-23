# Package initialization - runs when package is loaded
# This file must be named zzz.R so it loads last (after other R files)

# Package-level state for Python environment
.sparkbricks_env <- new.env(parent = emptyenv())
.sparkbricks_env$python_initialized <- FALSE
.sparkbricks_env$python_path <- NULL
.sparkbricks_env$dotenv_loaded <- FALSE


#' Load .env file (internal)
#'
#' Automatically searches for .env in current directory and parents.
#' Only loads once per session.
#'
#' @noRd
.load_dotenv <- function() {
  if (.sparkbricks_env$dotenv_loaded) {
    return(invisible(FALSE))
  }

  # Search for .env file
  env_file <- NULL
  search_dir <- getwd()
  for (i in 1:5) {
    candidate <- file.path(search_dir, ".env")
    if (file.exists(candidate)) {
      env_file <- candidate
      break
    }
    parent <- dirname(search_dir)
    if (parent == search_dir) break
    search_dir <- parent
  }

  if (!is.null(env_file) && file.exists(env_file)) {
    if (requireNamespace("dotenv", quietly = TRUE)) {
      dotenv::load_dot_env(env_file)
      .sparkbricks_env$dotenv_loaded <- TRUE

      # Add Databricks CLI to PATH if specified
      cli_path <- Sys.getenv("DATABRICKS_CLI_PATH", unset = "")
      if (nzchar(cli_path)) {
        cli_dir <- dirname(cli_path)
        current_path <- Sys.getenv("PATH")
        if (!grepl(cli_dir, current_path, fixed = TRUE)) {
          Sys.setenv(PATH = paste(cli_dir, current_path, sep = .Platform$path.sep))
        }
      }

      return(invisible(TRUE))
    }
  }

  .sparkbricks_env$dotenv_loaded <- TRUE  # Mark as attempted
  invisible(FALSE)
}


.onLoad <- function(libname, pkgname) {
  # Don't load .env in .onLoad - working directory may not be correct yet
  # It will be loaded lazily when needed

  # Check if user already set RETICULATE_PYTHON
  user_python <- Sys.getenv("RETICULATE_PYTHON", unset = "")
  if (nzchar(user_python)) {
    .sparkbricks_env$python_path <- user_python
    return(invisible())
  }

  # Check for SPARKBRICKS_PYTHON_ENV (our custom env var for the venv path)
  sparkbricks_env <- Sys.getenv("SPARKBRICKS_PYTHON_ENV", unset = "")
  if (nzchar(sparkbricks_env)) {
    python_path <- .find_python_in_venv(sparkbricks_env)
    if (!is.null(python_path)) {
      Sys.setenv(RETICULATE_PYTHON = python_path)
      .sparkbricks_env$python_path <- python_path
      return(invisible())
    }
  }

  # Don't auto-detect in .onLoad - let user specify via envname parameter
  # This avoids issues with working directory not being set yet
  invisible()
}


#' Find Python executable in a virtual environment
#' @noRd
.find_python_in_venv <- function(venv_path) {
  if (!dir.exists(venv_path)) {
    return(NULL)
  }

  # Windows: Scripts/python.exe, Unix: bin/python
  if (.Platform$OS.type == "windows") {
    python_path <- file.path(venv_path, "Scripts", "python.exe")
  } else {
    python_path <- file.path(venv_path, "bin", "python")
  }

  if (file.exists(python_path)) {
    return(normalizePath(python_path, winslash = "/"))
  }

  return(NULL)
}


#' Initialize Python environment (internal)
#'
#' This function ensures Python is properly initialized before use.
#' It handles the tricky parts of reticulate initialization that can
#' cause segfaults in non-interactive sessions (Rscript).
#'
#' Automatically loads .env file (if dotenv package installed) to get
#' SPARKBRICKS_PYTHON_ENV and other configuration.
#'
#' @param envname Path to virtual environment, or NULL for auto-detect
#' @param force Force re-initialization even if already initialized
#' @return The path to the Python executable being used
#' @noRd
.init_python <- function(envname = NULL, force = FALSE) {
  # Load .env file first (for SPARKBRICKS_PYTHON_ENV and other config)
  .load_dotenv()

  # If already initialized and not forcing, return cached path
  if (.sparkbricks_env$python_initialized && !force) {
    return(.sparkbricks_env$python_path)
  }

  # If envname provided, find Python in that venv
  if (!is.null(envname)) {
    python_path <- .find_python_in_venv(envname)
    if (is.null(python_path)) {
      stop(sprintf("Could not find Python in virtual environment: %s", envname))
    }
  } else {
    # Check for SPARKBRICKS_PYTHON_ENV again (may have been loaded from .env)
    sparkbricks_env <- Sys.getenv("SPARKBRICKS_PYTHON_ENV", unset = "")
    if (nzchar(sparkbricks_env)) {
      python_path <- .find_python_in_venv(sparkbricks_env)
    } else {
      python_path <- NULL
    }

    # If still not found, try to auto-detect
    if (is.null(python_path)) {
      python_path <- .auto_detect_python()
    }

    if (is.null(python_path)) {
      stop(
        "Could not find Python virtual environment. ",
        "Set SPARKBRICKS_PYTHON_ENV in .env file or environment, ",
        "or pass envname parameter."
      )
    }
  }

  # Set RETICULATE_PYTHON before any reticulate operations
  # This is critical for Rscript - must be set before Python loads
  current_retic_python <- Sys.getenv("RETICULATE_PYTHON", unset = "")
  if (!nzchar(current_retic_python)) {
    Sys.setenv(RETICULATE_PYTHON = python_path)
  }

  # Now use the virtualenv (this is safe after setting RETICULATE_PYTHON)
  if (!is.null(envname)) {
    reticulate::use_virtualenv(envname, required = TRUE)
  }

  # Force Python initialization by calling py_config()
  # This ensures Python is loaded before any imports
  tryCatch({
    config <- reticulate::py_config()
    .sparkbricks_env$python_initialized <- TRUE
    .sparkbricks_env$python_path <- python_path
  }, error = function(e) {
    stop(sprintf("Failed to initialize Python: %s", e$message))
  })

  return(python_path)
}


#' Auto-detect Python virtual environment
#' @noRd
.auto_detect_python <- function() {
  # Check common locations
  candidates <- c(
    ".venv",
    "venv",
    file.path(Sys.getenv("HOME"), ".virtualenvs", "sparkbricks")
  )

  # Also try here::here if available
  if (requireNamespace("here", quietly = TRUE)) {
    candidates <- c(
      here::here(".venv"),
      here::here("venv"),
      candidates
    )
  }

  for (venv in candidates) {
    python_path <- .find_python_in_venv(venv)
    if (!is.null(python_path)) {
      return(python_path)
    }
  }

  return(NULL)
}
