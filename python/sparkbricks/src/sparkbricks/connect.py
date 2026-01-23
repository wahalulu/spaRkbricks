"""Spark session connection management with multi-auth support.

Provides get_spark() for creating/retrieving a cached DatabricksSession,
and close_spark() for cleanup. Supports both OAuth and PAT authentication.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sparkbricks.auth import AuthType, _ensure_cli_path, get_workspace_client

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

# Module-level spark session (lazy initialized)
_spark: "SparkSession | None" = None
_env_loaded: bool = False


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available.

    Automatically searches current directory and parents for .env file.
    Only loads once per session.
    """
    global _env_loaded
    if _env_loaded:
        return

    try:
        from dotenv import load_dotenv

        load_dotenv()  # Searches current dir and parents
        _env_loaded = True
    except ImportError:
        pass  # dotenv not installed, skip silently


def get_spark(
    host: str | None = None,
    cluster_id: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    auto_start_cluster: bool = True,
) -> "SparkSession | None":
    """Get or create a Databricks Spark session with multi-auth support.

    Supports both OAuth (via Databricks CLI) and PAT authentication.
    Automatically loads configuration from .env file (if python-dotenv installed).
    Automatically starts the cluster if it's not running.

    Authentication priority (when auth_type="auto"):
    1. If token parameter provided -> PAT auth
    2. If DATABRICKS_TOKEN env var set -> PAT auth
    3. Otherwise -> OAuth via Databricks CLI profile

    Args:
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        cluster_id: Cluster ID (or set DATABRICKS_CLUSTER_ID in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        auto_start_cluster: If True, start cluster if not running

    Returns:
        SparkSession or None if connection fails

    Example:
        >>> # Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
        >>> spark = get_spark()
        >>> df = spark.sql("SELECT 1")

        >>> # Explicit PAT auth
        >>> spark = get_spark(token="dapi...")

        >>> # Explicit OAuth with specific profile
        >>> spark = get_spark(auth_type="oauth", profile="work")
    """
    global _spark

    if _spark is not None:
        return _spark

    # Load .env file if available (python-dotenv)
    _load_dotenv()

    # Import here to avoid circular imports
    from sparkbricks.cluster import ensure_cluster_running

    # Determine effective auth type
    effective_token = token or os.environ.get("DATABRICKS_TOKEN")
    effective_auth_type = auth_type
    if auth_type == "auto":
        effective_auth_type = "pat" if effective_token else "oauth"

    # Setup environment based on auth type
    if effective_auth_type == "pat":
        # PAT mode - set environment directly
        effective_host = host or os.environ.get("DATABRICKS_HOST")
        if not effective_host:
            print("ERROR: DATABRICKS_HOST required when using token authentication")
            return None
        if not effective_token:
            print("ERROR: Token required for PAT authentication")
            return None

        os.environ["DATABRICKS_HOST"] = effective_host
        os.environ["DATABRICKS_TOKEN"] = effective_token
        # Remove profile-based auth when using PAT
        os.environ.pop("DATABRICKS_CONFIG_PROFILE", None)
    else:
        # OAuth mode - ensure CLI is available
        _ensure_cli_path()
        if profile:
            os.environ["DATABRICKS_CONFIG_PROFILE"] = profile

    # Set environment if provided
    if host:
        os.environ["DATABRICKS_HOST"] = host
    if cluster_id:
        os.environ["DATABRICKS_CLUSTER_ID"] = cluster_id

    # Get effective cluster_id (from param or env)
    effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID")

    # Ensure cluster is running before connecting
    if auto_start_cluster and effective_cluster_id:
        if not ensure_cluster_running(
            cluster_id=effective_cluster_id,
            host=host or os.environ.get("DATABRICKS_HOST"),
            token=effective_token,
            profile=profile,
            auth_type=effective_auth_type,
        ):
            print("Failed to ensure cluster is running")
            return None

    try:
        from databricks.connect import DatabricksSession

        _spark = DatabricksSession.builder.getOrCreate()
        print(f"Spark connected (version {_spark.version})")
        return _spark
    except ImportError:
        print("databricks-connect not installed")
        print("Install with: uv pip install databricks-connect")
        return None
    except Exception as e:
        print(f"Databricks connection failed: {e}")
        if effective_auth_type == "oauth":
            print("Ensure 'databricks auth login' has been run")
        return None


def close_spark() -> None:
    """Close the cached Spark session and clear the module-level cache.

    Call this when you're done with the Spark session to properly clean up
    resources. This is especially important when called from R via reticulate
    to avoid orphaned Python sessions.

    Example:
        >>> spark = get_spark()
        >>> # ... do work ...
        >>> close_spark()  # Clean up
    """
    global _spark
    if _spark is not None:
        try:
            _spark.stop()
        except Exception as e:
            print(f"Warning: Error stopping Spark session: {e}")
        _spark = None
        print("Spark session closed")
