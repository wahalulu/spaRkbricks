"""Environment helpers for Databricks connectivity.

Provides functions to read Databricks configuration from environment variables.
"""

from __future__ import annotations

import os


def get_host() -> str | None:
    """Get Databricks host from environment.

    Returns:
        Databricks workspace URL (e.g., "https://adb-xxx.azuredatabricks.net")
        or None if not set.
    """
    return os.environ.get("DATABRICKS_HOST")


def get_cluster_id() -> str | None:
    """Get Databricks cluster ID from environment.

    Returns:
        Cluster ID (e.g., "0102-202223-xxxxx") or None if not set.
    """
    return os.environ.get("DATABRICKS_CLUSTER_ID")


def get_token() -> str | None:
    """Get Databricks Personal Access Token from environment.

    Returns:
        PAT token or None if not set.
    """
    return os.environ.get("DATABRICKS_TOKEN")


def get_auth_type() -> str:
    """Detect recommended auth type based on environment.

    Returns:
        "pat" if DATABRICKS_TOKEN is set, "oauth" otherwise.
    """
    return "pat" if os.environ.get("DATABRICKS_TOKEN") else "oauth"
