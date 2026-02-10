"""Authentication configuration for Databricks connectivity.

This module provides multi-auth support for connecting to Databricks:
- OAuth via Databricks CLI (automatic token refresh)
- Personal Access Token (PAT)
- Auto-detection based on available credentials
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from databricks.sdk import WorkspaceClient


class AuthType(Enum):
    """Supported authentication types."""

    OAUTH = "oauth"  # Via Databricks CLI profile
    PAT = "pat"  # Personal Access Token
    AUTO = "auto"  # Auto-detect (PAT if token present, else OAuth)


@dataclass
class AuthConfig:
    """Authentication configuration.

    Attributes:
        auth_type: The authentication method to use
        host: Databricks workspace URL
        cluster_id: Target cluster ID
        token: Personal Access Token (for PAT auth)
        profile: Databricks CLI profile name (for OAuth auth)
    """

    auth_type: AuthType
    host: str
    cluster_id: str
    token: str | None = None
    profile: str = "DEFAULT"

    @classmethod
    def from_params(
        cls,
        host: str | None = None,
        cluster_id: str | None = None,
        token: str | None = None,
        profile: str = "DEFAULT",
        auth_type: str | AuthType = "auto",
    ) -> "AuthConfig":
        """Create config from parameters with fallback to environment variables.

        Priority for each parameter:
        1. Function parameter (if provided)
        2. Environment variable
        3. Error (for required params)

        Auth type detection (when auth_type="auto"):
        1. If token parameter provided -> PAT
        2. If DATABRICKS_TOKEN env var set -> PAT
        3. Otherwise -> OAuth via CLI profile

        Args:
            host: Databricks workspace URL (or DATABRICKS_HOST env var)
            cluster_id: Cluster ID (or DATABRICKS_CLUSTER_ID env var)
            token: Personal Access Token (or DATABRICKS_TOKEN env var)
            profile: Databricks CLI profile name for OAuth
            auth_type: "auto", "oauth", or "pat"

        Returns:
            Configured AuthConfig instance

        Raises:
            ValueError: If required parameters are missing
        """
        # Convert string to enum if needed
        if isinstance(auth_type, str):
            auth_type = AuthType(auth_type.lower())

        # Resolve host
        effective_host = host or os.environ.get("DATABRICKS_HOST")
        if not effective_host:
            raise ValueError("host not provided and DATABRICKS_HOST not set")

        # Resolve cluster_id
        effective_cluster_id = cluster_id or os.environ.get("DATABRICKS_CLUSTER_ID")
        if not effective_cluster_id:
            raise ValueError("cluster_id not provided and DATABRICKS_CLUSTER_ID not set")

        # Resolve token (parameter > env var)
        effective_token = token or os.environ.get("DATABRICKS_TOKEN")

        # Determine auth type if auto
        if auth_type == AuthType.AUTO:
            auth_type = AuthType.PAT if effective_token else AuthType.OAUTH

        # Validate PAT auth has token
        if auth_type == AuthType.PAT and not effective_token:
            raise ValueError("PAT auth requires token parameter or DATABRICKS_TOKEN env var")

        return cls(
            auth_type=auth_type,
            host=effective_host,
            cluster_id=effective_cluster_id,
            token=effective_token,
            profile=profile,
        )


def _get_profile_config(profile: str) -> dict[str, str]:
    """Read configuration from ~/.databrickscfg for a given profile.

    This provides a fallback config source so that users who configure
    profiles in ~/.databrickscfg (via ``databricks auth login``) don't
    need to duplicate settings as environment variables.

    Args:
        profile: Profile name (e.g., "DEFAULT", "PROD")

    Returns:
        Dict with profile settings (host, cluster_id, token, etc.)
        Empty dict if profile not found or file doesn't exist.
    """
    import configparser

    config_path = Path.home() / ".databrickscfg"
    if not config_path.exists():
        return {}

    config = configparser.ConfigParser()
    config.read(config_path)

    if profile not in config:
        return {}

    return dict(config[profile])


def _ensure_cli_path() -> None:
    """Ensure the Databricks CLI is in PATH.

    Checks DATABRICKS_CLI_PATH env var first, then falls back to ~/bin.
    """
    # Check if DATABRICKS_CLI_PATH is set (from .env or otherwise)
    cli_path = os.environ.get("DATABRICKS_CLI_PATH")
    if cli_path:
        cli_dir = str(Path(cli_path).parent)
        if cli_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = cli_dir + os.pathsep + os.environ.get("PATH", "")
        return

    # Fallback to ~/bin
    cli_dir = Path.home() / "bin"
    if cli_dir.exists() and str(cli_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(cli_dir) + os.pathsep + os.environ.get("PATH", "")


def get_workspace_client(
    host: str | None = None,
    profile: str = "DEFAULT",
    token: str | None = None,
    auth_type: str | AuthType = "auto",
) -> "WorkspaceClient":
    """Get a Databricks WorkspaceClient with the specified authentication.

    Supports both OAuth (via Databricks CLI) and PAT authentication.

    Args:
        host: Databricks workspace URL (or uses DATABRICKS_HOST env var)
        profile: Databricks CLI profile name (for OAuth)
        token: Personal Access Token (for PAT)
        auth_type: "auto", "oauth", or "pat"

    Returns:
        Configured WorkspaceClient instance

    Example:
        >>> # Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
        >>> client = get_workspace_client()

        >>> # Explicit PAT auth
        >>> client = get_workspace_client(token="dapi...")

        >>> # Explicit OAuth with specific profile
        >>> client = get_workspace_client(auth_type="oauth", profile="work")
    """
    from databricks.sdk import WorkspaceClient

    # Convert string to enum if needed
    if isinstance(auth_type, str):
        auth_type = AuthType(auth_type.lower())

    # Resolve token
    effective_token = token or os.environ.get("DATABRICKS_TOKEN")

    # Auto-detect auth type
    if auth_type == AuthType.AUTO:
        auth_type = AuthType.PAT if effective_token else AuthType.OAUTH

    if auth_type == AuthType.PAT:
        # PAT authentication
        effective_host = host or os.environ.get("DATABRICKS_HOST")
        if not effective_host:
            raise ValueError("host required for PAT authentication")
        if not effective_token:
            raise ValueError("token required for PAT authentication")

        return WorkspaceClient(
            host=effective_host,
            token=effective_token,
        )
    else:
        # OAuth via CLI profile
        _ensure_cli_path()

        client_kwargs = {"profile": profile}
        if host:
            client_kwargs["host"] = host

        return WorkspaceClient(**client_kwargs)
