# Claude Code Instructions for spaRkbricks

## Project Overview

**spaRkbricks** is a monorepo containing Databricks connector packages for Python and R with multi-auth support (OAuth and PAT).

### Packages

1. **sparkbricks** (Python) - Databricks Connect wrapper with multi-auth
2. **spaRkbricks** (R) - R package that wraps sparkbricks via reticulate

## Repository Structure

```
spaRkbricks/
├── README.md                    # Project overview
├── LICENSE                      # MIT
├── pyproject.toml               # uv workspace root
├── CLAUDE.md                    # This file
├── .gitignore
│
├── python/                      # Python package
│   └── sparkbricks/
│       ├── pyproject.toml
│       └── src/sparkbricks/
│           ├── __init__.py      # Exports, Windows patch
│           ├── auth.py          # AuthType, AuthConfig, get_workspace_client
│           ├── connect.py       # get_spark, close_spark
│           ├── cluster.py       # Cluster management
│           ├── sql.py           # SQL helpers
│           ├── env.py           # Environment helpers
│           └── files.py         # Volume file operations
│
├── r/                           # R package
│   └── spaRkbricks/
│       ├── DESCRIPTION
│       ├── NAMESPACE
│       ├── LICENSE
│       └── R/
│           ├── zzz.R            # Package init, Python env
│           ├── auth.R           # Auth helpers
│           ├── connect.R        # Connection functions
│           └── cluster.R        # Cluster management
│
└── examples/
    ├── python/
    │   ├── 01_basic_connection.py
    │   ├── 02_pat_auth.py
    │   └── 03_oauth_auth.py
    └── r/
        ├── 01_basic_connection.R
        ├── 02_pat_auth.R
        └── 03_oauth_auth.R
```

## Key Concepts

### 1. Multi-Auth Support

The packages support two authentication methods:

- **OAuth**: Via Databricks CLI, automatic token refresh
- **PAT**: Personal Access Token, manual refresh needed

Auth detection priority:
1. `token` parameter → PAT
2. `DATABRICKS_TOKEN` env var → PAT
3. Otherwise → OAuth via CLI profile

### 2. R to Python Bridge

The R package uses reticulate to call Python:

```r
# In R
sparkbricks <- reticulate::import("sparkbricks")
spark <- sparkbricks$get_spark()
```

For OAuth, we extract the token from Python SDK for sparklyr:
```r
# Extract OAuth token for sparklyr
config = Config(host=..., auth_type='databricks-cli')
headers = config.authenticate()
token = headers.get('Authorization', '').replace('Bearer ', '')
```

### 3. databricks-connect Version

MUST match DBR version. Currently pinned to 17.3.x for DBR 17.3 LTS.

## Common Tasks

### Adding a New Function to sparkbricks

1. Add the function to the appropriate module (connect.py, cluster.py, etc.)
2. Add `token` and `auth_type` parameters for auth support
3. Export in `__init__.py`
4. Add corresponding R wrapper in spaRkbricks if needed

### Updating Authentication Logic

The `auth.py` module is the single source of truth for authentication:

```python
# auth.py
class AuthType(Enum):
    OAUTH = "oauth"
    PAT = "pat"
    AUTO = "auto"

def get_workspace_client(host, profile, token, auth_type):
    # Returns WorkspaceClient with appropriate auth
```

### Adding R Function

1. Add function to appropriate R file
2. Add roxygen2 documentation
3. Export in NAMESPACE
4. Regenerate docs: `roxygen2::roxygenise()`

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_CLUSTER_ID` | Target cluster |
| `DATABRICKS_TOKEN` | PAT (if using PAT auth) |
| `SPARKBRICKS_PYTHON_ENV` | Python venv path (for R) |
| `DATABRICKS_CLI_PATH` | Path to CLI executable |

## Testing

### Python

```bash
cd spaRkbricks
uv sync

# Test import
uv run python -c "from sparkbricks import get_spark; print('OK')"

# Test with actual connection (requires credentials)
uv run python examples/python/01_basic_connection.py
```

### R

```r
# Install
install.packages("r/spaRkbricks", repos = NULL, type = "source")

# Test import
library(spaRkbricks)
print(get_auth_type())
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `python/sparkbricks/src/sparkbricks/auth.py` | Central auth configuration |
| `python/sparkbricks/src/sparkbricks/connect.py` | Spark session management |
| `r/spaRkbricks/R/connect.R` | R connection functions |
| `r/spaRkbricks/R/zzz.R` | R package init, Python setup |
