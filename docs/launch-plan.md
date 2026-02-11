# Plan: Public Messaging & Launch Content for sparkbricks

## Context

sparkbricks works and solves real problems, but nobody outside the author knows it exists. The goal is to create the messaging, polish the README for public eyes, and draft launch content (announcement post + blog post) with an opinionated practitioner voice.

Key constraint: pysparklyr v0.2.0 now handles standalone OAuth from R without Posit Workbench. **Cluster auto-start** is the strongest unique differentiator, not OAuth.

---

## Deliverables

### 1. README restructure (`README.md`)

**Problem:** Current README is ~354 lines. Too long for a first impression. Leads with "OAuth from R is essentially unsolved" which is now inaccurate. API reference tables add bulk without helping the "should I use this?" decision.

**Changes:**
- Rewrite the one-liner pitch: *"sparkbricks makes Databricks Connect work the way you assumed it already did — from your local machine, in R or Python, without fighting five tools that don't talk to each other."*
- **Add a before/after code block as the first visual.** The "before" code is ~20 lines of manual reticulate + SDK + token parsing + cluster polling. The "after" is `sc <- spark_connect_databricks()`. This contrast is the conversion moment. Source for the "before" code: `r/spaRkbricks/R/connect.R:131-148` (OAuth token extraction) + `python/sparkbricks/src/sparkbricks/cluster.py:220-337` (cluster polling).
- Replace "OAuth from R is essentially unsolved without this" with "Auth that auto-detects and just works" (OAuth, PAT, profiles)
- Shorten the 6-problem section to a concise bulleted list (not numbered deep-dives)
- Move the API reference tables to `docs/api-reference.md`
- Target: ~180 lines (down from 354)

**Structure:**
```
# sparkbricks
One-liner pitch

## Before / After (code contrast — the hook)

## What It Does (bulleted, 6 items)

## How It Fits Together (architecture diagram — keep existing)

## Quick Start (install + .env + connect, compact)

## Authentication (keep existing section, minor edits)

## Environment Variables (keep)

## Requirements (keep, compressed)

## Full API Reference → link to docs/api-reference.md
```

### 2. API reference doc (`docs/api-reference.md`)

Move the Python and R API tables from the README here. No new content — just relocated.

### 3. Announcement post (`docs/announcement-post.md`)

For r/rstats, r/databricks, Posit Community, Mastodon. ~200 words for Reddit, shorter for Mastodon.

**Structure:**
- The setup: "If you use R with Databricks, you know the pain"
- What it is: one function handles auth, cluster start, connection
- Before/after code (abbreviated)
- How it relates to pysparklyr: "pysparklyr v0.2.0 recently added standalone OAuth, which is great. sparkbricks adds cluster auto-start, config resolution, and a unified R+Python API."
- Link + call to action

**Tone rules:**
- "I built this because X was broken" — not "excited to announce"
- Acknowledge pysparklyr improvements upfront (prevents the top comment being a correction)
- First person singular

### 4. Blog post (`docs/blog-post.md`)

~2,000-2,500 words. Opinionated practitioner voice.

**Title:** "Local R Development on Databricks Is Broken. Here's How I Fixed It."

**Sections:**
1. **The Workflow Nobody Talks About** (~300w) — Scene-setting. R user on a Databricks team. Prefers local IDE + git. Databricks Connect exists for this. In theory.
2. **What's Actually Broken** (~500w) — The five-tool problem. Concrete failures: cluster auto-stop, OAuth, reticulate segfaults, config scatter. "The Posit partnership solves this if you pay for Workbench. If you don't, you're on your own."
3. **What sparkbricks Does** (~500w) — Architecture. Design principles. Before/after code. Cluster auto-start as the killer feature.
4. **What It Doesn't Do** (~200w) — Honest limitations. Not streaming, not a notebook replacement, DBR version pinning, single cluster per session.
5. **Why Not Contribute Upstream?** (~300w) — The integration layer is nobody's responsibility. Each tool is fine on its own. The gap is between them.
6. **Where This Is Going** (~300w) — Arrow-native, ADBC, DuckDB caching, unified API. Vision without overpromising.
7. **Try It** (~200w) — Install commands, .env template, "If you're an R user on a Databricks team, I want to hear from you."

---

## What NOT to Say

| Avoid | Why | Say instead |
|-------|-----|-------------|
| "Only way to get OAuth from R" | pysparklyr v0.2.0 does this | "Handles OAuth, PAT, and profiles with auto-detection" |
| "pysparklyr doesn't support OAuth" | It does now | "pysparklyr recently added standalone OAuth. sparkbricks goes further with cluster lifecycle and config resolution." |
| "Posit only cares about paid customers" | Inflammatory, partially inaccurate | "The Posit integration is optimized for managed environments. sparkbricks is for local development." |
| "Replaces pysparklyr/sparklyr" | It wraps them | "Sits on top of the full stack" |
| "Zero configuration" | You still need host + cluster_id | "Minimal configuration" |

**Own boldly:** Cluster auto-start. No other R-side tool does it. It's verifiable in the code. Lead with it everywhere.

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `README.md` | Restructure (shorten, add before/after, fix OAuth claim) |
| `docs/api-reference.md` | New — relocated API tables from README |
| `docs/announcement-post.md` | New — Reddit/Mastodon/Posit Community post drafts |
| `docs/blog-post.md` | New — long-form opinionated blog post |

## Verification

- Read the final README and confirm it's under 200 lines
- Confirm no inaccurate OAuth-exclusivity claims remain
- Confirm the before/after code contrast is accurate (matches actual implementation in connect.R and cluster.py)
- Confirm API reference tables are in docs/api-reference.md and linked from README
