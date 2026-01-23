"""sparkbricks: Databricks connector with multi-auth support (OAuth and PAT).

This package provides Databricks connectivity via Databricks Connect with support
for both OAuth (via Databricks CLI) and Personal Access Token (PAT) authentication.

Example:
    from sparkbricks import get_spark, sql

    # Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
    spark = get_spark()
    df = sql("SELECT * FROM catalog.schema.table")

    # Explicit PAT auth
    spark = get_spark(token="dapi...")

    # Explicit OAuth
    spark = get_spark(auth_type="oauth", profile="work")
"""

__version__ = "0.1.0"


def _patch_pyspark_for_windows() -> None:
    """Patch PySpark Unix-only components for Windows compatibility.

    PySpark's accumulators module uses UnixStreamServer which doesn't exist on Windows.
    This patches socketserver to provide a dummy class before PySpark imports.
    """
    import sys

    if sys.platform != "win32":
        return

    import socketserver

    if hasattr(socketserver, "UnixStreamServer"):
        return

    # Create a dummy Unix stream server for Windows
    class _DummyUnixStreamServer:
        """Dummy class to satisfy PySpark imports on Windows."""

        def __init__(self, *args, **kwargs):
            raise NotImplementedError("Unix sockets not available on Windows")

    socketserver.UnixStreamServer = _DummyUnixStreamServer  # type: ignore[attr-defined]


# Apply patch immediately on import
_patch_pyspark_for_windows()

# Public API exports
from sparkbricks.auth import AuthType, AuthConfig, get_workspace_client
from sparkbricks.connect import get_spark, close_spark
from sparkbricks.cluster import (
    cluster_status,
    start_cluster,
    stop_cluster,
    ensure_cluster_running,
)
from sparkbricks.sql import sql, table, tables, describe, count
from sparkbricks.env import get_host, get_cluster_id, get_token, get_auth_type
from sparkbricks.files import download_file, upload_file, list_volume

__all__ = [
    # Auth
    "AuthType",
    "AuthConfig",
    "get_workspace_client",
    # Connection
    "get_spark",
    "close_spark",
    # Cluster management
    "cluster_status",
    "start_cluster",
    "stop_cluster",
    "ensure_cluster_running",
    # SQL helpers
    "sql",
    "table",
    "tables",
    "describe",
    "count",
    # Environment
    "get_host",
    "get_cluster_id",
    "get_token",
    "get_auth_type",
    # File operations
    "download_file",
    "upload_file",
    "list_volume",
]
