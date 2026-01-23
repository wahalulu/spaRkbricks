# spaRkbricks

Databricks connector with multi-auth support for Python and R.

**Key Features:**
- **OAuth support** - Automatic token refresh via Python SDK (not available in pysparklyr!)
- **PAT support** - Personal Access Token authentication
- **Cluster management** - Start, stop, and check cluster status
- **Dual language** - Works from both Python and R

## Why spaRkbricks?

The official Databricks Connect for R ([pysparklyr](https://github.com/mlverse/pysparklyr)) only supports Personal Access Token (PAT) authentication. This means:
- Tokens expire and need manual renewal
- No automatic token refresh for long-running sessions
- Poor experience for interactive analysis

**spaRkbricks** solves this by routing OAuth through the Python SDK, which handles token refresh automatically. You get the best of both worlds: OAuth convenience with R's analytical power.

## Installation

### Python

```bash
# Using uv (recommended)
uv pip install sparkbricks

# Or from source
cd python/sparkbricks
uv pip install -e .
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

### Python

```python
from sparkbricks import get_spark, sql, cluster_status

# Auto-detect auth (PAT if DATABRICKS_TOKEN set, else OAuth)
spark = get_spark()

# Run a query
df = sql("SELECT * FROM catalog.schema.table LIMIT 10")

# Check cluster status
status = cluster_status()
print(f"Cluster: {status}")
```

### R

```r
library(spaRkbricks)

# Auto-detect auth
sc <- spark_connect_databricks()

# Use with dplyr
library(dplyr)
tbl(sc, "catalog.schema.table") |>
  filter(x > 10) |>
  collect()

# Disconnect properly
spark_disconnect_databricks(sc)
```

## Authentication

### Option 1: OAuth (Recommended for Interactive Use)

Uses Databricks CLI for automatic token refresh.

**Setup:**
```bash
# Install Databricks CLI
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Login (creates OAuth session)
databricks auth login --host https://your-workspace.azuredatabricks.net
```

**Usage:**
```python
# Python - OAuth is automatic when DATABRICKS_TOKEN is not set
spark = get_spark(auth_type="oauth", profile="DEFAULT")
```

```r
# R
sc <- spark_connect_databricks(auth_type = "oauth", profile = "DEFAULT")
```

### Option 2: Personal Access Token (PAT)

Direct token authentication. Good for CI/CD and automation.

**Setup:**
```bash
# Set in .env or environment
export DATABRICKS_TOKEN=dapi123456789...
```

**Usage:**
```python
# Python
spark = get_spark(token="dapi...")
# Or auto-detect from DATABRICKS_TOKEN
spark = get_spark()
```

```r
# R
sc <- spark_connect_databricks(token = "dapi...")
# Or auto-detect from DATABRICKS_TOKEN
sc <- spark_connect_databricks()
```

### Auth Priority

When `auth_type="auto"` (default):
1. `token` parameter → PAT auth
2. `DATABRICKS_TOKEN` env var → PAT auth
3. Otherwise → OAuth via Databricks CLI

## API Reference

### Python (`sparkbricks`)

| Function | Description |
|----------|-------------|
| `get_spark()` | Get or create a Spark session |
| `close_spark()` | Close the Spark session |
| `cluster_status()` | Get cluster status |
| `start_cluster()` | Start a cluster |
| `stop_cluster()` | Stop a cluster |
| `ensure_cluster_running()` | Ensure cluster is running |
| `sql()` | Run SQL query and display results |
| `table()` | Get table as DataFrame |
| `tables()` | List tables in schema |
| `describe()` | Describe table schema |
| `count()` | Count rows in table |
| `download_file()` | Download file from Volume |
| `upload_file()` | Upload file to Volume |
| `list_volume()` | List files in Volume |

### R (`spaRkbricks`)

| Function | Description |
|----------|-------------|
| `spark_connect_databricks()` | Connect to Databricks |
| `spark_disconnect_databricks()` | Disconnect properly |
| `cluster_status()` | Get cluster status |
| `start_cluster()` | Start a cluster |
| `stop_cluster()` | Stop a cluster |
| `ensure_cluster_running()` | Ensure cluster is running |
| `get_auth_type()` | Detect current auth type |
| `check_auth()` | Check auth credentials |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_HOST` | Workspace URL | Yes |
| `DATABRICKS_CLUSTER_ID` | Target cluster ID | Yes |
| `DATABRICKS_TOKEN` | PAT token | For PAT auth |
| `SPARKBRICKS_PYTHON_ENV` | Python venv path | For R package |
| `DATABRICKS_CLI_PATH` | Path to CLI | Optional |

## Requirements

### Python
- Python 3.10+
- databricks-connect >= 17.3.0, < 18.0.0
- databricks-sdk >= 0.20.0

### R
- R >= 4.0
- reticulate >= 1.35
- sparklyr >= 1.8.0
- Python environment with sparkbricks installed

## License

MIT
