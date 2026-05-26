# Agent Memory SQLite Schema

SQLite is the source of truth for the MVP. Obsidian files are generated mirrors.

## Project Identity

`project_id` is `sha256(abs_project_path)[:16]`.

## Tables

- `projects`: one row per project path.
- `episodes`: task history and outcome summaries.
- `semantic_facts`: durable facts, preferences, and project knowledge.
- `reflections`: lessons, mistakes, and future rules.
- `code_files`: lightweight file-level wiki index.
- `code_symbols`: lightweight symbol-level wiki index.

## Governance Fields

Phase 2 adds memory governance metadata while keeping SQLite as the source of truth:

- `status`: `active`, `stale`, `merged`, `archived`, or `rejected`.
- `scope`: where a fact or reflection applies.
- `evidence`: source file, episode, user instruction, or command output behind the memory.
- `last_used_at` and `use_count`: lightweight usage signals updated by context queries.
- `reviewed_at`: when a memory was checked or consolidated.
- `merged_into_id`: replacement memory after consolidation.
- `stale_reason`: why a memory should no longer be trusted directly.

`episodes` also track `importance`, usage counts, and derived fact/reflection ids.

## Staleness

`semantic_facts` and `reflections` include `is_stale` for backwards compatibility. New governance commands also set `status = 'stale'`. Stale records are excluded from `context` by default.

## Confidence

`semantic_facts.confidence` and `reflections.confidence` are 0.0 to 1.0 scores. User-provided facts should usually be 1.0.

## Lifecycle

```text
active -> stale -> archived
active -> merged -> replacement active memory
active -> rejected
episode/reflection -> promoted semantic fact
```

Query commands consume governance metadata. Maintain commands create, review, merge, stale, archive, reject, or promote memory records.
