"""Cluster management functions with multi-auth support.

Provides functions to check status, start, and stop Databricks clusters.
Supports both OAuth (via Databricks CLI) and PAT authentication.
"""

from __future__ import annotations

import os
import time

from sparkbricks.auth import _ensure_cli_path, _get_profile_config, get_workspace_client
from sparkbricks.connect import _load_dotenv


def cluster_status(
    cluster_id: str | None = None,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
) -> str | None:
    """Get the current status of a Databricks cluster.

    Automatically loads configuration from .env file (if python-dotenv installed).
    Supports both OAuth and PAT authentication.

    Args:
        cluster_id: Databricks cluster ID (or set DATABRICKS_CLUSTER_ID in .env)
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"

    Returns:
        Cluster state string (e.g., "RUNNING", "TERMINATED") or None on error

    Example:
        >>> # Auto-detect auth
        >>> status = cluster_status()
        >>> print(f"Cluster is {status}")

        >>> # With PAT
        >>> status = cluster_status(token="dapi...")
    """
    # Load .env file if available
    _load_dotenv()

    # Get cluster_id from param or env
    effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID")
    if not effective_cluster_id:
        print("ERROR: cluster_id not provided and DATABRICKS_CLUSTER_ID not set")
        return None

    try:
        client = get_workspace_client(host, profile, token, auth_type)
        cluster = client.clusters.get(effective_cluster_id)
        return cluster.state.value
    except Exception as e:
        print(f"Failed to get cluster status: {e}")
        return None


def start_cluster(
    cluster_id: str | None = None,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    wait: bool = True,
    timeout_minutes: int = 15,
) -> bool:
    """Start a Databricks cluster.

    Automatically loads configuration from .env file (if python-dotenv installed).
    Supports both OAuth and PAT authentication.

    Args:
        cluster_id: Databricks cluster ID (or set DATABRICKS_CLUSTER_ID in .env)
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        wait: If True, wait for cluster to reach RUNNING state
        timeout_minutes: Max time to wait if wait=True

    Returns:
        True if cluster started successfully, False otherwise

    Example:
        >>> start_cluster(wait=True)
        Starting cluster...
        Cluster running (took 120s)
        True
    """
    # Load .env file if available
    _load_dotenv()

    # Get cluster_id from param or env
    effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID")
    if not effective_cluster_id:
        print("ERROR: cluster_id not provided and DATABRICKS_CLUSTER_ID not set")
        return False

    try:
        from databricks.sdk.service.compute import State

        client = get_workspace_client(host, profile, token, auth_type)
        cluster = client.clusters.get(effective_cluster_id)
        state = cluster.state

        if state == State.RUNNING:
            print(f"Cluster {effective_cluster_id} is already running")
            return True

        if state not in (State.TERMINATED, State.TERMINATING):
            print(f"Cluster {effective_cluster_id} is in state {state.value}, cannot start")
            return False

        print(f"Starting cluster {effective_cluster_id}...")
        client.clusters.start(effective_cluster_id)

        if not wait:
            print("Start command sent (not waiting)")
            return True

        # Wait for cluster
        return ensure_cluster_running(
            effective_cluster_id, host, token, profile, auth_type, timeout_minutes
        )

    except Exception as e:
        print(f"Failed to start cluster: {e}")
        return False


def stop_cluster(
    cluster_id: str | None = None,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    wait: bool = False,
) -> bool:
    """Stop a Databricks cluster.

    Automatically loads configuration from .env file (if python-dotenv installed).
    Supports both OAuth and PAT authentication.

    Args:
        cluster_id: Databricks cluster ID (or set DATABRICKS_CLUSTER_ID in .env)
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        wait: If True, wait for cluster to reach TERMINATED state

    Returns:
        True if cluster stop initiated successfully, False otherwise

    Example:
        >>> stop_cluster()
        Stopping cluster...
        Stop command sent
        True
    """
    # Load .env file if available
    _load_dotenv()

    # Get cluster_id from param or env
    effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID")
    if not effective_cluster_id:
        print("ERROR: cluster_id not provided and DATABRICKS_CLUSTER_ID not set")
        return False

    try:
        from databricks.sdk.service.compute import State

        client = get_workspace_client(host, profile, token, auth_type)
        cluster = client.clusters.get(effective_cluster_id)
        state = cluster.state

        if state == State.TERMINATED:
            print(f"Cluster {effective_cluster_id} is already terminated")
            return True

        print(f"Stopping cluster {effective_cluster_id}...")
        client.clusters.delete(effective_cluster_id)  # delete = terminate, not destroy

        if not wait:
            print("Stop command sent")
            return True

        # Wait for termination
        print("Waiting for cluster to stop", end="", flush=True)
        start_time = time.time()
        timeout_seconds = 300  # 5 min max for stopping

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print("\nTimeout waiting for cluster to stop")
                return False

            cluster = client.clusters.get(effective_cluster_id)
            state = cluster.state

            if state == State.TERMINATED:
                print(f"\nCluster stopped (took {int(elapsed)}s)")
                return True

            print(".", end="", flush=True)
            time.sleep(5)

    except Exception as e:
        print(f"Failed to stop cluster: {e}")
        return False


def ensure_cluster_running(
    cluster_id: str | None = None,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    timeout_minutes: int = 15,
) -> bool:
    """Ensure the Databricks cluster is running, starting it if necessary.

    Automatically loads configuration from .env file (if python-dotenv installed)
    and from ~/.databrickscfg profile.
    Supports both OAuth and PAT authentication.

    Configuration precedence for cluster_id:
    1. Function parameter (if provided)
    2. DATABRICKS_CLUSTER_ID environment variable
    3. cluster_id from ~/.databrickscfg profile

    Args:
        cluster_id: Databricks cluster ID (or set DATABRICKS_CLUSTER_ID in .env)
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        timeout_minutes: Max time to wait for cluster to start

    Returns:
        True if cluster is running, False if failed to start

    Example:
        >>> ensure_cluster_running()
        Cluster: TERMINATED
        Starting cluster...
        Waiting for cluster to start.........
        Cluster running (took 95s)
        True

        >>> # Use cluster_id from PROD profile in ~/.databrickscfg
        >>> ensure_cluster_running(profile="PROD")
    """
    # Load .env file if available
    _load_dotenv()

    # Read profile config from ~/.databrickscfg as fallback
    profile_config = _get_profile_config(profile) if profile else {}

    # Get cluster_id: parameter > env var > profile config
    effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID") or profile_config.get("cluster_id")
    if not effective_cluster_id:
        print("ERROR: cluster_id not provided, not in env, and not in profile")
        return False

    try:
        from databricks.sdk.service.compute import State
    except ImportError:
        print("databricks-sdk not installed")
        print("Install with: uv pip install databricks-sdk")
        return False

    # Get client with appropriate auth
    try:
        client = get_workspace_client(host, profile, token, auth_type)
    except Exception as e:
        print(f"Failed to create Databricks client: {e}")
        return False

    # Get cluster state
    try:
        cluster = client.clusters.get(effective_cluster_id)
        state = cluster.state
        print(f"Cluster {effective_cluster_id}: {state.value}")
    except Exception as e:
        print(f"Failed to get cluster state: {e}")
        return False

    # If already running, we're done
    if state == State.RUNNING:
        return True

    # If terminated or terminating, start it
    if state in (State.TERMINATED, State.TERMINATING):
        print(f"Starting cluster {effective_cluster_id}...")
        try:
            client.clusters.start(effective_cluster_id)
        except Exception as e:
            print(f"Failed to start cluster: {e}")
            return False

    # Wait for cluster to be running
    print("Waiting for cluster to start", end="", flush=True)
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\nTimeout waiting for cluster after {timeout_minutes} minutes")
            return False

        try:
            cluster = client.clusters.get(effective_cluster_id)
            state = cluster.state
        except Exception as e:
            print(f"\nFailed to get cluster state: {e}")
            return False

        if state == State.RUNNING:
            print(f"\nCluster running (took {int(elapsed)}s)")
            return True

        if state in (State.ERROR, State.UNKNOWN):
            print(f"\nCluster in error state: {state.value}")
            return False

        print(".", end="", flush=True)
        time.sleep(10)
