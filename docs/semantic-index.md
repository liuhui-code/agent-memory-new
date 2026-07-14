# Semantic Index

`SemanticIndex v1` is the language-neutral bridge between learned source code, the SQLite code graph, change-impact analysis, repository design, and Incident diagnosis.

## Runtime Shape

```text
learn-entry / learn-path / wiki-index
  -> language detection
  -> LanguageAdapter
       ArkTS static adapter
       TypeScript static adapter
       future compiler/LSP/SCIP exact adapter
  -> semantic-index/v1 batch
  -> code_symbols metadata + versioned memory_edges
  -> architecture slice / impact scope / Incident causal candidates
```

Learning remains the only automatic indexing entry point. There is no fifth Skill, daemon, graph database, vector database, or runtime LLM call.

## Stable Contract

A batch declares its schema, adapter identity/version, language, capabilities, source digests, entities, relations, and explicit gaps. Entities use deterministic symbol keys and include qualified name, signature, source span, export status, and evidence class. Relations use normalized names:

- `calls`
- `reads_state` / `writes_state`
- `implements` / `extends` / `overrides`
- `registers_callback`
- `exposes_api` / `consumes_api`
- `awaits`

Malformed, oversized, unsupported, ambiguous, or unresolved output is rejected or reported as a gap. The core consumers do not import ArkTS or TypeScript parsing code.

## Evidence Semantics

Evidence precision and causal role are separate dimensions:

- Precision: `exact`, `static`, `heuristic`, `inferred`.
- Incident role: `observed`, `supports`, `possible`, `inferred`.

The built-in lightweight adapters emit `static`, never `exact`. A matched runtime log is `observed`; its enclosing symbol `supports` the inspection path; static code relations are only `possible`. This prevents a statically reachable method from being presented as a proven runtime cause.

## Incremental Refresh

Partial learning captures existing reverse dependents before replacing symbol rows. It rebuilds the changed files and those dependents, restores incoming semantic edges to the new symbol ids, and supersedes weaker duplicate active edges. Target resolution uses indexed symbol key and file/qualified-name lookups rather than loading the whole graph.

`parse_stats.semantic_index` reports adapter coverage, files, entities, extracted/emitted relations, unresolved relations, gaps, and adapter errors.

## Consumer Limits

- Architecture slices remain depth 2, at most 80 nodes and 160 edges.
- Impact analysis reads direct file/symbol endpoints and one-hop reverse consumers.
- Incident semantic traversal remains depth 2 and at most 16 edges per log anchor.
- Normal FTS5 query behavior is unchanged.

## Evolution

An exact es2panda, language-server, or SCIP provider can be added later by implementing `LanguageAdapter`, declaring capabilities/toolchain version, emitting source digests, and passing the same conformance suite. Registration is the only core change; graph, storage, design, impact, and Incident logic remain language-neutral.
