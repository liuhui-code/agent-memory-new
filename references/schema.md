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

## Staleness

`semantic_facts` and `reflections` include `is_stale`. Stale records are excluded from `context` by default.

## Confidence

`semantic_facts.confidence` is a 0.0 to 1.0 score. User-provided facts should usually be 1.0.
