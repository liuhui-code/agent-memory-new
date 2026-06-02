# Project Memory Refresh And Retirement Plan

This document defines the MVP-safe way to keep Agent Memory aligned with a codebase that changes over time.

The goal is not "relearn everything and overwrite history." The goal is:

```text
remember what was learned
-> refresh those learned scopes when the source changes
-> retire obsolete structural records
-> surface semantic drift for review
-> keep experience review human-guided
```

The user-facing interface remains fixed at four skills:

- `agent-memory-learn`
- `agent-memory-query`
- `agent-memory-maintain`
- `agent-memory-reflect`

No fifth skill is introduced.

## Why This Exists

Projects keep moving:

- files are added
- files are removed
- symbols change behavior
- logs change meaning
- old business summaries stop matching current code

If the memory system never refreshes learned scopes, query quality drifts downward and later reflections or skill candidates become anchored to outdated code.

## Design Principles

1. SQLite remains the source of truth.
2. Obsidian remains a generated mirror.
3. Structure can refresh automatically.
4. Business meaning should be reviewed, not blindly overwritten.
5. Experience should be reviewed, not silently deleted.

## What Gets Refreshed

### Structural Memory

These records should track current source closely:

- `code_files`
- `code_symbols`
- `code_log_statements`
- `memory_edges`

When a learned scope is refreshed:

- changed files are re-indexed
- removed files have their structural rows retired from the code wiki
- edges are rebuilt

### Semantic Memory

These records are not overwritten automatically by a refresh:

- `business_summary`
- `business_terms`
- reflections and experiences

Instead, refresh produces drift targets so maintain review can decide where semantic enrichment should be rerun.

## Learn Scope Manifest

Every structural learning command records a persistent scope manifest in SQLite:

- `wiki-index`
- `learn-path`
- `learn-entry`

Each manifest stores:

- `scope_type`: `project`, `path`, or `entry`
- `source_root`
- `target_path` or `entry_path`
- `depth`
- `mode`
- `file_snapshot`
- `file_count`
- timestamps

This is the minimum data needed to replay a previously learned scope later.

## Refresh Command

The maintain-side refresh command is:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --json
```

Optional scoped refresh:

```bash
python tools/agent_memory.py maintain-refresh-scope --project . --scope-id 3 --json
```

The command:

1. loads active learned scopes
2. reconstructs the file set for each scope from current source
3. compares the old and new file snapshots
4. refreshes current structural records
5. retires structural rows for removed files in that scope
6. emits semantic drift review targets

## Refresh Output

Each scope refresh reports:

- `added_files`
- `changed_files`
- `removed_files`
- `unchanged_count`
- `parse_stats`
- `semantic_review_targets`

`semantic_review_targets` is the low-risk bridge back into governance:

- changed files suggest semantic review
- added files suggest semantic enrichment
- removed files suggest retirement review

## Retirement Policy

### Structural retirement

Safe to automate:

- removed file -> remove file, symbol, log rows for that file
- rebuild edges

### Semantic retirement

Do not automate destructive deletion.

Instead:

- mark drift targets for `learn-business`
- route correction experiences through `maintain-plan`
- let human review decide whether a business summary, experience, or candidate skill has gone stale

## MVP Phases

### Phase 1: implemented now

- persistent `learn_scopes` table
- scope recording from `wiki-index`, `learn-path`, `learn-entry`
- `maintain-refresh-scope`
- structural refresh of current files
- structural retirement of removed files
- drift output for semantic review

### Phase 2: next safe extension

- `maintain-plan` reads recent refresh drift
- emits `review_semantic_drift`
- emits `mark_experience_stale_if_anchor_removed`

### Phase 3: later refinement

- scope-level health metrics
- stale skill-pattern suggestions when source anchors disappear
- vault dashboards for refresh history and semantic drift

## Success Criteria

The feature is working if:

1. previously learned scopes can be replayed without re-entering paths manually
2. removed files disappear from structural code-wiki query results after refresh
3. added and changed files become visible to semantic review
4. the runtime does not silently wipe business semantics or experiences

## Non-Goals For This MVP

- no daemon watcher
- no cron scheduler
- no vector database
- no graph database
- no full automatic experience invalidation
- no automatic formal skill demotion
