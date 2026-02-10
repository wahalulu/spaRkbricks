# spaRkbricks

An integration layer that makes Databricks Connect actually usable for data teams, from both Python and R.

## The Problem

Connecting to a remote Databricks cluster from a local machine requires you to correctly orchestrate **five separate tools** that were never designed to work together seamlessly: `databricks-connect`, `databricks-sdk`, `pyspark`, `sparklyr`, and `reticulate`. Each has its own auth model, configuration, and failure modes.

**spaRkbricks** unifies them into a single coherent system.

```python
# Python
from sparkbricks import get_spark, sql

spark = get_spark()  # handles auth, starts cluster, connects
df = sql("SELECT * FROM catalog.schema.table")
```

```r
# R
library(spaRkbricks)

sc <- spark_connect_databricks()  # same thing, from R
tbl(sc, "catalog.schema.table") |> collect()
```

## Why Not Just Use databricks-connect / sparklyr / pyspark Directly?

You can. But you'll end up solving these problems yourself:

### 1. OAuth from R is essentially unsolved without this

sparklyr needs a **token string**. OAuth gives you a **refresh flow managed by the Databricks CLI**. These two things don't talk to each other.

Without spaRkbricks, an R user wanting OAuth has to: import the Databricks Python SDK via reticulate, instantiate a `Config` object with `auth_type='databricks-cli'`, call `config.authenticate()` to get HTTP headers, parse the Bearer token out of the Authorization header, inject it into the `DATABRICKS_TOKEN` env var, and *then* connect via sparklyr.

Most R users don't know how to do this. Most tutorials say "just use a PAT" -- which expires, can't be refreshed programmatically, and is a security concern to store in `.env` files.

### 2. The reticulate initialization order causes segfaults

If `RETICULATE_PYTHON` isn't set **before** reticulate loads, especially when running via `Rscript` (non-interactive), Python picks up the system interpreter instead of your venv. This causes silent wrong-package-version errors, outright segfaults with no error message, and hours of debugging.

The R package handles this entire problem: venv detection, `RETICULATE_PYTHON` ordering, `py_config()` forcing. This isn't boilerplate -- it's knowledge earned through painful debugging that most users would never figure out on their own.

### 3. Scripts fail when clusters auto-stop

Databricks clusters auto-terminate after inactivity (typically 10-30 minutes). Without spaRkbricks:
- You run a script, it fails with a cryptic gRPC error
- You go to the Databricks UI, click "Start"
- You wait 3-5 minutes
- You re-run your script
- Repeat multiple times per day

With `auto_start_cluster=True` (the default), this entire failure mode disappears. Your script just works, whether the cluster is running or not.

### 4. Switching between OAuth and PAT requires different code paths

A data team typically needs:
- **OAuth** for interactive local development (token auto-refreshes)
- **PAT** for CI/CD or scheduled scripts
- **Different profiles** for UAT vs PROD clusters

Without spaRkbricks, these are completely different code paths with different env vars, different session creation patterns, and different error modes. With spaRkbricks, it's one parameter: `auth_type="auto"` handles detection, or you explicitly choose `"oauth"` / `"pat"`.

### 5. Configuration is scattered across three places

Users end up with settings in:
- `.env` files (project-specific)
- Environment variables (shell-specific)
- `~/.databrickscfg` profiles (machine-wide, created by `databricks auth login`)

Without spaRkbricks, you pick one and hardcode against it. With the 3-tier fallback (`parameter > env var > profile config`), everything resolves correctly regardless of where the user put their config.

### 6. Volume file operations need their own auth

The Databricks SDK files API requires a `WorkspaceClient` with proper auth. Even if you're already connected with a Spark session, you need to create a separate SDK client for file operations. spaRkbricks shares the same auth context across session, cluster, and file operations.

## How It Fits Together

```
┌──────────────────────────────────────────────────┐
│                  spaRkbricks                     │
│  auth, cluster lifecycle, config, volume files   │
├────────────────────┬─────────────────────────────┤
│  Python            │  R                          │
│  databricks-connect│  sparklyr + reticulate      │
│  databricks-sdk    │  (calls Python under hood)  │
│  pyspark           │                             │
└────────────────────┴─────────────────────────────┘
```

spaRkbricks is not a replacement for any of these tools. It's the integration layer that makes them behave as one system:

- **pyspark** -- Python API for Spark. DataFrames, SQL. Doesn't know about Databricks auth or remote clusters.
- **databricks-connect** -- Provides `DatabricksSession` so you can run Spark locally against a remote cluster. Expects you to handle auth and have the cluster running.
- **sparklyr** -- R interface to Spark. Can connect to Databricks, but needs a token string and a running cluster.
- **databricks-sdk** -- Python SDK for the Databricks REST API (clusters, files, workspace). Not a Spark execution engine.
- **reticulate** -- R-to-Python bridge. Powerful but has initialization ordering pitfalls that cause segfaults.

## Installation

### Python

```bash
# Using uv (recommended)
uv pip install sparkbricks

# Or from source
cd python/sparkbricks
uv pip install -e .

# With .env file support
uv pip install sparkbricks[dotenv]
```

### R

```r
# From source
install.packages("path/to/spaRkbricks/r/spaRkbricks", repos = NULL, type = "source")

# Ensure Python environment is set
Sys.setenv(SPARKBRICKS_PYTHON_ENV = "path/to/.venv")
```

## Quick Start

### Configuration

Create a `.env` file in your project:

```bash
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
DATABRICKS_CLUSTER_ID=0102-202223-xxxxx

# For PAT auth (optional - if not set, uses OAuth)
# DATABRICKS_TOKEN=dapi...
```

Or rely on your `~/.databrickscfg` profile (created by `databricks auth login`):

```ini
# ~/.databrickscfg
[DEFAULT]
host = https://your-workspace.azuredatabricks.net
cluster_id = 0102-202223-xxxxx
```

Configuration precedence: **function parameter > environment variable > `~/.databrickscfg` profile**.

### Python

```python
from sparkbricks import get_spark, close_spark, sql, cluster_status

# Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
# Auto-starts cluster if needed
spark = get_spark()

# Run a query
df = sql("SELECT * FROM catalog.schema.table LIMIT 10")

# Check cluster status
status = cluster_status()
print(f"Cluster: {status}")

# Clean up
close_spark()
```

```python
# Use a named profile from ~/.databrickscfg
spark = get_spark(profile="PROD")

# Explicit PAT auth
spark = get_spark(token="dapi...")

# Explicit OAuth with a specific profile
spark = get_spark(auth_type="oauth", profile="work")
```

### R

```r
library(spaRkbricks)

# Auto-detect auth, auto-start cluster
sc <- spark_connect_databricks()

# Use with dplyr
library(dplyr)
tbl(sc, "catalog.schema.table") |>
  filter(x > 10) |>
  collect()

# Disconnect properly (closes both R and Python sessions)
spark_disconnect_databricks(sc)
```

```r
# Explicit PAT auth
sc <- spark_connect_databricks(token = "dapi...")

# Explicit OAuth with a specific profile
sc <- spark_connect_databricks(auth_type = "oauth", profile = "work")
```

## Authentication

### Option 1: OAuth (Recommended for Interactive Use)

Uses Databricks CLI for automatic token refresh. Tokens are managed by the SDK -- no manual renewal needed.

**Setup:**
```bash
# Install Databricks CLI
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Login (creates OAuth session stored in ~/.databrickscfg)
databricks auth login --host https://your-workspace.azuredatabricks.net
```

**Usage:**
```python
# Python - OAuth is automatic when DATABRICKS_TOKEN is not set
spark = get_spark()
```

```r
# R - OAuth token is extracted from Python SDK and injected for sparklyr
sc <- spark_connect_databricks()
```

### Option 2: Personal Access Token (PAT)

Direct token authentication. Useful for CI/CD, automation, and environments where OAuth browser flow isn't available.

**Setup:**
```bash
# Set in .env or environment
export DATABRICKS_TOKEN=dapi123456789...
```

**Usage:**
```python
# Python - auto-detected from env var
spark = get_spark()

# Or pass explicitly
spark = get_spark(token="dapi...")
```

```r
# R
sc <- spark_connect_databricks(token = "dapi...")
```

### Auth Detection Priority

When `auth_type="auto"` (default):
1. `token` parameter provided -> PAT auth
2. `DATABRICKS_TOKEN` env var set -> PAT auth
3. Otherwise -> OAuth via Databricks CLI profile

## API Reference

### Python (`sparkbricks`)

#### Connection
| Function | Description |
|----------|-------------|
| `get_spark()` | Get or create a Spark session (handles auth, cluster start, config) |
| `close_spark()` | Close the Spark session and clean up |

#### Cluster Management
| Function | Description |
|----------|-------------|
| `cluster_status()` | Get current cluster state (RUNNING, TERMINATED, etc.) |
| `start_cluster()` | Start a cluster with optional wait |
| `stop_cluster()` | Stop a cluster |
| `ensure_cluster_running()` | Check and start cluster if needed |

#### SQL Helpers
| Function | Description |
|----------|-------------|
| `sql()` | Run SQL query and display results |
| `table()` | Get table as DataFrame |
| `tables()` | List tables in a schema |
| `describe()` | Describe table schema (columns and types) |
| `count()` | Count rows in a table |

#### Volume File Operations
| Function | Description |
|----------|-------------|
| `download_file()` | Download file from Unity Catalog Volume |
| `upload_file()` | Upload file to Unity Catalog Volume |
| `list_volume()` | List files in a Volume path |

#### Auth
| Function | Description |
|----------|-------------|
| `get_workspace_client()` | Get a configured Databricks SDK WorkspaceClient |
| `AuthType` | Enum: OAUTH, PAT, AUTO |
| `AuthConfig` | Dataclass for auth configuration |

#### Environment
| Function | Description |
|----------|-------------|
| `get_host()` | Get DATABRICKS_HOST from env |
| `get_cluster_id()` | Get DATABRICKS_CLUSTER_ID from env |
| `get_token()` | Get DATABRICKS_TOKEN from env |
| `get_auth_type()` | Detect auth type from env ("pat" or "oauth") |

### R (`spaRkbricks`)

| Function | Description |
|----------|-------------|
| `spark_connect_databricks()` | Connect to Databricks (handles auth, cluster start, R/Python bridge) |
| `spark_disconnect_databricks()` | Disconnect both R and Python sessions |
| `cluster_status()` | Get cluster status |
| `start_cluster()` | Start a cluster |
| `stop_cluster()` | Stop a cluster |
| `ensure_cluster_running()` | Ensure cluster is running |
| `get_auth_type()` | Detect current auth type |
| `check_auth()` | Verify auth credentials are available |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_HOST` | Workspace URL | Yes (or in profile) |
| `DATABRICKS_CLUSTER_ID` | Target cluster ID | Yes (or in profile) |
| `DATABRICKS_TOKEN` | PAT token | Only for PAT auth |
| `DATABRICKS_CONFIG_PROFILE` | CLI profile name | No (default: DEFAULT) |
| `SPARKBRICKS_PYTHON_ENV` | Python venv path | For R package |
| `DATABRICKS_CLI_PATH` | Path to CLI executable | Optional |

## Requirements

### Python
- Python 3.10+
- databricks-connect >= 17.3.0, < 18.0.0 (must match your DBR version)
- databricks-sdk >= 0.20.0

### R
- R >= 4.0
- reticulate >= 1.35
- sparklyr >= 1.8.0
- Python environment with sparkbricks installed

## License

MIT
