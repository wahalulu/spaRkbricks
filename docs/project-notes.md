# Project Notes: sparkbricks

Internal design document capturing the rationale, positioning, and future direction of the project. Last updated: 2026-02-10.

---

## 1. What This Project Is

sparkbricks is an integration layer that makes Databricks Connect usable for data teams working locally in R and Python. It sits on top of five tools that were never designed to work together seamlessly -- `databricks-connect`, `databricks-sdk`, `pyspark`, `sparklyr`, and `reticulate` -- and unifies them into a single coherent system.

It is not a replacement for any of those tools. It is the glue that makes them behave as one.

### Origin

The project was extracted from two internal repositories (`pulseflow-analytics` and `pf-data-qa`) where Databricks connectivity patterns were developed for healthcare analytics work. The shared connectivity code was generalized into a standalone package with multi-auth support (OAuth and PAT) that any team can use.

---

## 2. Problems It Solves

### 2.1 OAuth from R

This is the primary motivating problem. sparklyr needs a token string. OAuth provides a refresh flow managed by the Databricks CLI. These don't talk to each other.

Without sparkbricks, an R user wanting OAuth must: import the Databricks Python SDK via reticulate, instantiate a `Config` object with `auth_type='databricks-cli'`, call `config.authenticate()` to get HTTP headers, parse the Bearer token from the Authorization header, inject it into `DATABRICKS_TOKEN`, and then connect via sparklyr.

Most R users cannot do this. Most tutorials tell them to use PATs, which expire and are a security concern.

### 2.2 reticulate Initialization Ordering

If `RETICULATE_PYTHON` is not set before reticulate loads, especially in non-interactive `Rscript` sessions, Python picks up the system interpreter instead of the project venv. This causes silent wrong-package-version errors or segfaults with no error message.

The R package handles venv detection, `RETICULATE_PYTHON` ordering, and `py_config()` forcing. This is knowledge earned through debugging that users would not figure out on their own.

### 2.3 Cluster Auto-Start

Databricks clusters auto-terminate after inactivity (typically 10-30 minutes). Without auto-start, scripts fail with cryptic gRPC errors. The user must manually start the cluster in the UI, wait, and retry. This happens multiple times per day.

With `auto_start_cluster=True` (the default), the tool checks cluster status, starts it if needed, polls until RUNNING, and then connects. The failure mode disappears entirely.

### 2.4 Auth Switching

Teams typically need OAuth for interactive development, PAT for CI/CD, and different profiles for UAT vs PROD. Without sparkbricks, these are completely different code paths. With sparkbricks, `auth_type="auto"` detects the right method, or the user explicitly chooses.

### 2.5 Configuration Scatter

Settings end up in `.env` files (project-specific), environment variables (shell-specific), and `~/.databrickscfg` profiles (machine-wide). sparkbricks resolves all three with a consistent precedence: function parameter > environment variable > profile config.

### 2.6 Volume File Operations with Shared Auth

The Databricks SDK files API requires a `WorkspaceClient` with proper auth, separate from the Spark session. sparkbricks shares the same auth context across session, cluster, and file operations.

---

## 3. How It Relates to Existing Tools

```
Tool                    What it does                          What it doesn't do
---                     ---                                   ---
pyspark                 Python Spark API (DataFrames, SQL)    Databricks auth, remote clusters
databricks-connect      Remote DatabricksSession via gRPC     Auth management, cluster lifecycle
sparklyr                R interface to Spark via dplyr         OAuth, cluster lifecycle
databricks-sdk          REST API client (clusters, files)     Spark execution
reticulate              R-to-Python bridge                    Safe initialization ordering
```

sparkbricks orchestrates all five. The architecture:

```
+-------------------------------------------------+
|                 sparkbricks                      |
|  auth, cluster lifecycle, config, volume files   |
+---------------------+---------------------------+
|  Python             |  R                         |
|  databricks-connect |  sparklyr + reticulate     |
|  databricks-sdk     |  (calls Python under hood) |
|  pyspark            |                            |
+---------------------+---------------------------+
```

---

## 4. The Databricks/Posit Partnership

### Overview

Posit (formerly RStudio) is Databricks' Developer Tools Partner of the Year for 2025 (second consecutive year). The partnership delivers:

- **Posit Workbench**: Native Databricks integration with managed OAuth credentials. RStudio Pro and Positron run against Databricks compute with admin-configured auth.
- **Posit Connect**: Deploys R/Python content with automatic Databricks credential management.
- **Positron**: Posit's next-gen IDE (successor to RStudio) with built-in Databricks support.

### pysparklyr Auth Evolution

| Version | Auth Changes |
|---------|-------------|
| v0.1.0  | PAT only |
| v0.1.2  | Added "Databricks OAuth" -- specifically for Posit Connect integration |
| v0.1.7  | "Deferring to SDK" for more flexible auth; serverless support |
| v0.2.0  | Uses Posit Workbench config for OAuth tokens; Viewer OAuth credentials |

pysparklyr also added `.databrickscfg` support (GitHub issue #88, merged via PR #89).

### What This Means for sparkbricks

**If the user has Posit Workbench (paid):** OAuth is handled by Posit infrastructure. Admin configures credentials, Workbench manages tokens, pysparklyr picks them up. sparkbricks' OAuth value is reduced.

**If the user has standalone R/RStudio/Positron (free):** The OAuth situation is unclear. pysparklyr v0.1.7 "defers to SDK" which may pick up CLI-based OAuth from `.databrickscfg`, but the primary OAuth path is routed through Posit products. sparkbricks' explicit token extraction still fills a gap here.

**What pysparklyr does not do regardless of version:**
- Cluster auto-start
- Unified Python + R API
- Volume file operations
- .env file loading
- 3-tier config resolution
- SQL convenience helpers

### Strategic Implication

The Posit/Databricks partnership is optimized for teams that pay for Posit Workbench. sparkbricks serves a different niche: making Databricks work from a local machine without managed infrastructure. Posit has no incentive to close this gap -- it would undercut their paid product.

### Open Question

It is worth testing whether a clean install of pysparklyr v0.1.7+ with a `.databrickscfg` profile from `databricks auth login` works for OAuth from a local machine without Posit Workbench. If it does, sparkbricks' R OAuth story shifts from "the only way" to "a simpler way with more features." If it doesn't, sparkbricks remains the only option for free-tier R users.

---

## 5. Alternative Approaches Considered

### SQL Warehouses + databricks-sql-connector

For teams that primarily run SQL and collect results (no Spark DataFrames needed):
- SQL warehouses auto-start, have serverless options, and are cheaper
- Native OAuth support without token extraction
- No DBR version pinning
- Returns pandas/Arrow, not Spark DataFrames
- Does not work with sparklyr's lazy dplyr evaluation

### ODBC from R

Bypasses Python entirely using the Simba ODBC driver:
- Pure R, no reticulate, no segfaults
- Works with SQL warehouses
- ODBC driver installation is platform-specific and painful
- No Spark DataFrames or dplyr pushdown

### Databricks SDK Only (StatementExecutionAPI)

The SDK handles OAuth natively. Can execute SQL on warehouses without databricks-connect:
- No version pinning
- SQL-only, no Spark DataFrames
- Synchronous, needs manual pagination for large results

### Contributing OAuth Upstream to pysparklyr

Fix the root cause instead of wrapping around it:
- Benefits the whole community
- Don't control the release timeline
- Still doesn't solve cluster auto-start, config unification, etc.

### PATs Everywhere

Simplest approach. Give everyone a token, put it in `.env`:
- Zero infrastructure
- Tokens expire, manual renewal
- Security concern (plaintext tokens)
- Long sessions break when tokens expire

### When sparkbricks Is the Right Call

The project is specifically right when a team needs all of these together:
1. Full Spark DataFrames (not just SQL results)
2. Both R and Python
3. OAuth with auto-refresh
4. Local development against remote clusters
5. Interactive analysis where clusters may be stopped

---

## 6. Target Audience

### Primary: Data Scientists

Their workflow is: get data, pull local, explore/model/visualize, iterate. They don't care about Spark -- they care about tibbles, DataFrames, ggplot2, scikit-learn. The cluster is a data source.

Why sparkbricks maps to them:
- Arrow transfer (fast data, not Spark semantics)
- Local caching (rerun exploration without re-querying)
- OAuth without thinking
- Cluster auto-start

### Primary: R Users on Databricks Teams

The most underserved niche. Databricks is Python-first. sparklyr is second-class. OAuth doesn't work natively. Documentation and examples are Python. These users constantly fight the platform.

### Secondary: Mixed R/Python Teams

Common in pharma, healthcare, government, academia. The R people use tidyverse, the Python people use pandas/polars. A unified API is a coordination win.

### Secondary: "Notebook Refugees"

People forced into Databricks notebooks who prefer local IDEs, git workflows, and their own tools. sparkbricks gives them a path back to local development.

### Not the Audience: Data Engineers

They work inside Databricks with notebooks, jobs, and pipeline tools. A local-first analytics tool solves the wrong problem for them.

### Not the Audience: SQL-Only Analysts

They use the Databricks SQL Editor, Power BI, Tableau, or DBeaver. These tools already work.

---

## 7. Expanded Vision

The current tool solves the connection problem. The larger opportunity is a local-first analytics toolkit for Databricks.

### Unified API with Arrow

Instead of Spark DataFrames, return Arrow tables that convert to tibbles (R) or polars/pandas (Python). Same function names in both languages. The user never touches a Spark DataFrame.

```r
# R
con <- bk_connect()
df <- bk_query(con, "SELECT * FROM table")  # returns tibble via Arrow
```

```python
# Python
con = bk.connect()
df = bk.query(con, "SELECT * FROM table")  # returns polars via Arrow
```

### Multiple Backends

If the API is "query -> Arrow -> local frame," the backend can vary:
- **Databricks cluster** via databricks-connect (full Spark)
- **SQL warehouse** via ADBC/Flight SQL (cheaper, serverless, auto-starts)
- **Local DuckDB** for cached data or small datasets

The user writes the same code regardless.

### Local Caching

```r
df <- bk_query(con, "SELECT * FROM big_table", cache = TRUE)
# First time: queries Databricks, caches as local Parquet
# Second time: reads from local cache, never hits Databricks
```

DuckDB can query the local Parquet cache with SQL for further analysis.

### ADBC as Primary Transport

Arrow Database Connectivity (ADBC) with Databricks Flight SQL:
- Native Arrow results (no conversion overhead)
- Works with SQL warehouses (no cluster needed)
- No databricks-connect version pinning (the biggest maintenance pain)
- OAuth support built in
- Works from both R and Python

For SQL workloads (most analytics), ADBC + SQL warehouse could replace databricks-connect. Only users who need PySpark transformations or sparklyr lazy evaluation would need a cluster.

### Revised Architecture

```
+-------------------------------------------------+
|                  brickster                       |
|       unified API: connect, query, collect       |
|      returns: tibble (R) / polars (Python)       |
+--------------+--------------+-------------------+
|   Backend    |   Backend    |   Backend          |
|   ADBC /     |   databricks |   local            |
|   Flight SQL |   -connect   |   DuckDB / Parquet |
|  (SQL wh)    |  (cluster)   |   (cached data)    |
+--------------+--------------+-------------------+
|             Arrow (transfer format)              |
+-------------------------------------------------+
|   Auth layer: OAuth / PAT / profile config       |
|   (what sparkbricks does today)                  |
+-------------------------------------------------+
```

### Sequencing

1. Ship current sparkbricks (auth + cluster + convenience) -- it already solves real pain
2. Add Arrow-native query path (`.toArrow()` for databricks-connect, ADBC for SQL warehouses)
3. Unified API with identical function names in R and Python
4. Local caching via DuckDB/Parquet
5. Consider renaming to reflect the broader scope

---

## 8. Implicit Assumptions and Prerequisites

These must be true for the tool to work. Each is a potential failure point that should be documented for users.

### Network and Connectivity

| Assumption | Failure Mode |
|-----------|-------------|
| Machine can reach workspace on port 443 | Timeout, cryptic gRPC error |
| gRPC/HTTP2 not blocked by firewall or proxy | Timeout, looks like network issue |
| Connection is stable (survives sleep/wake, VPN drops) | Silent broken pipe mid-session |

databricks-connect uses gRPC over HTTP/2. Some corporate firewalls allow regular HTTPS but block gRPC. The user gets a timeout with no indication it's a network issue. Flaky VPNs and laptop sleep/wake cycles drop the session silently with no auto-reconnect.

### Security and Permissions

| Assumption | Failure Mode |
|-----------|-------------|
| User has workspace access | Login error |
| User has "Can Attach To" or "Can Restart" on cluster | Permissions error |
| Unity Catalog grants on tables/volumes | Access denied on query |
| Admin hasn't disabled Databricks Connect | Vague permissions error |
| Admin hasn't disabled PAT tokens or restricted OAuth scopes | Auth failure |

**Data leaves the cloud.** When results are collected, they travel from the cluster to the local machine over TLS. Some organizations prohibit this. sparkbricks does not add encryption beyond what Databricks/TLS provides, and does not enforce data governance on the local side.

**Tokens are stored in plaintext.** PAT tokens in `.env` files and OAuth refresh tokens in `~/.databrickscfg` are plaintext on disk. No secrets management is provided.

### Databricks Workspace Configuration

| Assumption | Failure Mode |
|-----------|-------------|
| Unity Catalog enabled | Volume operations fail, table namespacing differs |
| Databricks Connect not disabled at workspace level | Connection refused |
| Cluster has Connect enabled (default on DBR 13.3+) | Connection refused |

### Cluster Requirements

| Assumption | Failure Mode |
|-----------|-------------|
| Cluster exists and user knows its ID | Not found error |
| DBR version matches databricks-connect pin (17.3.x) | Version mismatch error |
| Cluster has sufficient resources | OOM on cluster side |

The DBR version pinning is the most fragile assumption. Every cluster runtime upgrade is a potential breaking change. This is the strongest argument for the ADBC/SQL warehouse path in the expanded vision.

### Local Environment

| Assumption | Failure Mode |
|-----------|-------------|
| Python 3.10+ in a virtual environment | Import errors |
| For R: correct Python found by reticulate before init | Wrong packages or segfault |
| For R: reticulate >= 1.35, sparklyr >= 1.8.0 | Version incompatibilities |
| Sufficient local RAM for query results | OOM or swap death |

No local Java is required. databricks-connect v2 (13.3+) uses gRPC, not a local Spark installation.

### Workflow Assumptions

| Assumption | Failure Mode |
|-----------|-------------|
| Working locally, not in a Databricks notebook | Unnecessary overhead if already in notebook |
| Interactive or batch analysis, not streaming | No streaming support |
| Results fit in local memory | OOM |
| One cluster at a time per session | Module-level cache limits to single session |

---

## 9. Maintenance Concerns

### databricks-connect Version Pinning

The dependency `databricks-connect>=17.3.0,<18.0.0` must match the target cluster's DBR version exactly. When Databricks releases a new LTS runtime, the project must update the pin, test, and release. This creates a coupling between the cluster admin's upgrade schedule and the package version.

The ADBC/SQL warehouse path in the expanded vision avoids this entirely.

### Upstream Changes in pysparklyr

As pysparklyr evolves its auth support, some of sparkbricks' R-side value may diminish. Monitoring pysparklyr releases for OAuth improvements is important. If standalone OAuth (without Posit Workbench) starts working reliably in pysparklyr, the messaging should shift to emphasize the other features (auto-start, unified API, convenience helpers).

### Databricks SDK API Changes

The `databricks-sdk` is evolving rapidly. File operations, cluster management, and auth flows may change. Pin to `>=0.20.0` but monitor for breaking changes.

---

## 10. Naming

The current name "spaRkbricks" uses the R convention of capitalizing R in package names. It's awkward as a repo/project name (mixed case, the R pun only matters for the R package).

Candidates considered:

| Name | Python pkg | R pkg | Notes |
|------|-----------|-------|-------|
| brickster | brickster | bricksteR | Playful "Databricks master." Short, memorable. |
| sparklink | sparklink | spaRklink | "Links" to Spark/Databricks. Clean. |
| dbxconnect | dbxconnect | dbxconnect | dbx is common Databricks shorthand. |
| bricklyr | bricklyr | bricklyr | Follows tidyverse naming convention. |
| kiln | kiln | kiln | Where bricks are fired. Very short, unique. |

If the project expands to the full vision (Arrow, multi-backend, caching), the name should reflect the broader scope rather than just the connection layer.

---

## 11. Release Plan

### Phase 1: Ship What Exists (Current)

The auth + cluster auto-start + convenience helpers already solve real pain. Ship as a GitHub-installable package for early feedback.

- Finalize name
- Make installable from GitHub in one line (Python and R)
- Write a before/after walkthrough (40 lines of boilerplate vs. `get_spark()`)
- Post to Posit Community, r/rstats, r/databricks, Mastodon #rstats

### Phase 2: Arrow-Native Query Path

- Add `.toArrow()` path for databricks-connect results
- Explore ADBC + Flight SQL for SQL warehouse support
- Return tibbles (R) and polars DataFrames (Python) by default

### Phase 3: Unified API

- Same function names in R and Python
- Backend abstraction (cluster vs. warehouse vs. local)
- Local caching via DuckDB/Parquet

### Phase 4: Community and Packaging

- PyPI and CRAN submission
- Documentation site
- Example notebooks/vignettes

---

## References

- Posit + Databricks integrations: https://posit.co/use-cases/databricks/
- Posit 2025 Databricks Partner of the Year: https://posit.co/blog/posit-2025-databricks-developer-tools-partner-of-the-year/
- Posit-Databricks product announcement (Aug 2025): https://posit.co/blog/posit-databricks-product-announcement-aug-2025/
- sparklyr Databricks Connect docs: https://spark.posit.co/deployment/databricks-connect.html
- pysparklyr GitHub: https://github.com/mlverse/pysparklyr
- pysparklyr changelog: https://cran.r-project.org/web/packages/pysparklyr/news/news.html
- pysparklyr .databrickscfg support: https://github.com/mlverse/pysparklyr/issues/88
- Databricks + Posit partnership blog: https://www.databricks.com/blog/databricks-and-posit-announce-new-integrations
- ADBC (Arrow Database Connectivity): https://arrow.apache.org/adbc/
