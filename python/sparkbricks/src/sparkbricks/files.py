"""File operations for Databricks Unity Catalog Volumes with multi-auth support.

Provides functions to download (and upload) files from/to Databricks Volumes.
Volume paths follow the format: /Volumes/<catalog>/<schema>/<volume>/<path>
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from sparkbricks.auth import get_workspace_client
from sparkbricks.connect import _load_dotenv


def download_file(
    volume_path: str,
    local_path: str | Path | None = None,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    overwrite: bool = False,
) -> Path:
    """Download a file from a Databricks Unity Catalog Volume.

    Automatically loads configuration from .env file (if python-dotenv installed).
    Supports both OAuth and PAT authentication.

    Args:
        volume_path: Full path to file in volume (e.g., /Volumes/catalog/schema/volume/data/file.csv)
        local_path: Local destination path. If None, downloads to current directory
                    with the same filename. If a directory, uses the source filename.
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        overwrite: If True, overwrite existing local file. Default False.

    Returns:
        Path to the downloaded local file

    Raises:
        ValueError: If volume_path is invalid
        FileExistsError: If local file exists and overwrite=False
        Exception: If download fails

    Example:
        >>> # Download to current directory
        >>> local = download_file("/Volumes/uat_cha_bronze/data/exports/report.csv")

        >>> # Download with PAT auth
        >>> local = download_file(
        ...     "/Volumes/uat_cha_bronze/data/exports/report.csv",
        ...     token="dapi..."
        ... )
    """
    # Load .env file if available
    _load_dotenv()

    # Validate volume path
    if not volume_path.startswith("/Volumes/"):
        raise ValueError(
            f"Invalid volume path: {volume_path}. "
            "Must start with /Volumes/<catalog>/<schema>/<volume>/"
        )

    # Parse the filename from volume path
    source_filename = Path(volume_path).name

    # Determine local destination
    if local_path is None:
        local_dest = Path.cwd() / source_filename
    else:
        local_dest = Path(local_path)
        if local_dest.is_dir():
            local_dest = local_dest / source_filename

    # Check if file exists
    if local_dest.exists() and not overwrite:
        raise FileExistsError(
            f"Local file already exists: {local_dest}. " "Use overwrite=True to replace."
        )

    # Ensure parent directory exists
    local_dest.parent.mkdir(parents=True, exist_ok=True)

    # Get workspace client with appropriate auth
    effective_host = host or os.environ.get("DATABRICKS_HOST")
    client = get_workspace_client(host=effective_host, profile=profile, token=token, auth_type=auth_type)

    # Download the file
    print(f"Downloading: {volume_path}")
    print(f"         to: {local_dest}")

    try:
        response = client.files.download(volume_path)

        # Write to local file
        with open(local_dest, "wb") as f:
            # response.contents is a BinaryIO object
            shutil.copyfileobj(response.contents, f)

        print(f"Downloaded {local_dest.stat().st_size:,} bytes")
        return local_dest

    except Exception as e:
        # Clean up partial file if it exists
        if local_dest.exists():
            local_dest.unlink()
        raise Exception(f"Failed to download {volume_path}: {e}") from e


def upload_file(
    local_path: str | Path,
    volume_path: str,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
    overwrite: bool = False,
) -> str:
    """Upload a local file to a Databricks Unity Catalog Volume.

    Automatically loads configuration from .env file (if python-dotenv installed).
    Supports both OAuth and PAT authentication.

    Args:
        local_path: Path to local file to upload
        volume_path: Destination path in volume (e.g., /Volumes/catalog/schema/volume/data/file.csv)
                     If ends with /, uses the source filename.
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"
        overwrite: If True, overwrite existing file in volume. Default False.

    Returns:
        The volume path where file was uploaded

    Raises:
        FileNotFoundError: If local file doesn't exist
        ValueError: If volume_path is invalid
        Exception: If upload fails

    Example:
        >>> upload_file("./data/report.csv", "/Volumes/uat_cha_sandbox/mvaisman/uploads/report.csv")

        >>> # With PAT auth
        >>> upload_file("./data/report.csv", "/Volumes/...", token="dapi...")
    """
    # Load .env file if available
    _load_dotenv()

    # Validate local file
    local_file = Path(local_path)
    if not local_file.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")
    if not local_file.is_file():
        raise ValueError(f"Not a file: {local_path}")

    # Validate volume path
    if not volume_path.startswith("/Volumes/"):
        raise ValueError(
            f"Invalid volume path: {volume_path}. "
            "Must start with /Volumes/<catalog>/<schema>/<volume>/"
        )

    # If volume_path is a directory, append filename
    if volume_path.endswith("/"):
        volume_path = volume_path + local_file.name

    # Get workspace client with appropriate auth
    effective_host = host or os.environ.get("DATABRICKS_HOST")
    client = get_workspace_client(host=effective_host, profile=profile, token=token, auth_type=auth_type)

    print(f"Uploading: {local_file}")
    print(f"       to: {volume_path}")

    try:
        with open(local_file, "rb") as f:
            client.files.upload(volume_path, f, overwrite=overwrite)

        print(f"Uploaded {local_file.stat().st_size:,} bytes")
        return volume_path

    except Exception as e:
        raise Exception(f"Failed to upload to {volume_path}: {e}") from e


def list_volume(
    volume_path: str,
    host: str | None = None,
    token: str | None = None,
    profile: str = "DEFAULT",
    auth_type: str = "auto",
) -> list[dict]:
    """List files and directories in a Databricks Unity Catalog Volume path.

    Supports both OAuth and PAT authentication.

    Args:
        volume_path: Path in volume (e.g., /Volumes/catalog/schema/volume/ or subdirectory)
        host: Databricks workspace URL (or set DATABRICKS_HOST in .env)
        token: Personal Access Token (or set DATABRICKS_TOKEN in .env)
        profile: Databricks CLI profile name (for OAuth)
        auth_type: "auto", "oauth", or "pat"

    Returns:
        List of dicts with file info: {'name': str, 'path': str, 'is_dir': bool, 'size': int}

    Example:
        >>> files = list_volume("/Volumes/uat_cha_bronze/data/exports/")
        >>> for f in files:
        ...     print(f"{f['name']} - {f['size']} bytes")
    """
    # Load .env file if available
    _load_dotenv()

    # Validate volume path
    if not volume_path.startswith("/Volumes/"):
        raise ValueError(
            f"Invalid volume path: {volume_path}. "
            "Must start with /Volumes/<catalog>/<schema>/<volume>/"
        )

    # Ensure path ends with /
    if not volume_path.endswith("/"):
        volume_path = volume_path + "/"

    # Get workspace client with appropriate auth
    effective_host = host or os.environ.get("DATABRICKS_HOST")
    client = get_workspace_client(host=effective_host, profile=profile, token=token, auth_type=auth_type)

    try:
        entries = client.files.list_directory_contents(volume_path)

        result = []
        for entry in entries:
            result.append(
                {
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_directory,
                    "size": entry.file_size if hasattr(entry, "file_size") else 0,
                }
            )

        return result

    except Exception as e:
        raise Exception(f"Failed to list {volume_path}: {e}") from e
