# SemanticIndex Code Graph and Causal Chain Plan

**Goal:** Introduce a language-neutral semantic indexing layer whose first adapters improve ArkTS and TypeScript code relationships, then use those relationships to sharpen repository design, impact analysis, and goal-oriented Incident diagnosis.

**Architecture:** Learning remains the only automatic indexing entry. Language adapters emit `SemanticIndex v1` batches containing capabilities, stable entities, normalized relations, provenance, evidence class, and explicit gaps. SQLite `code_symbols` and `memory_edges` remain the source of truth. Code graph and Incident consumers read normalized relations without importing ArkTS-specific parser code.

**Boundaries:** Keep four public Skills, `tools/agent_memory.py` as the stable runtime, no vector/graph database, no daemon, no runtime LLM, no complete global data-flow graph, and every Python file at or below 500 lines. Built-in parsers must report `static`, never `exact`; a future compiler/SCIP adapter can emit `exact` through the same protocol.

## Phase 1: Stable Semantic IR

- [x] Define `semantic-index/v1` entities, relations, capabilities, gaps, adapter identity, source digest, and schema validation.
- [x] Define a `LanguageAdapter` protocol and registry independent of ArkTS syntax.
- [x] Normalize endpoint identity as deterministic file or symbol keys.
- [x] Bound one batch by files, entities, relations, and diagnostics.
- [x] Preserve evidence roles separately from evidence precision.

Acceptance:

- Malformed batches and unsupported schema versions fail clearly.
- Adapter output is serializable and deterministic.
- Core graph/Incident modules depend only on the semantic protocol.

## Phase 2: Symbol Metadata and Incremental Governance

- [x] Add backward-compatible symbol key, qualified name, signature, source span, adapter, source digest, and evidence-class columns to `code_symbols`.
- [x] Add indexed lookup by project/symbol key and project/file/qualified name.
- [x] Expand partial edge rebuilds to include existing reverse dependents before replacing target symbol ids.
- [x] Supersede lower-authority duplicate semantic relations while preserving active-edge lifecycle metadata.
- [x] Return semantic parse counts, adapter coverage, gaps, and edge counts in learning feedback.

Acceptance:

- Existing databases migrate idempotently.
- Partial relearn restores incoming relationships to replaced symbols.
- No full-project semantic scan is required for a narrow refresh.

## Phase 3: ArkTS Semantic Adapter

- [x] Parse ArkTS classes, structs, interfaces, methods, functions, state, fields, imports, inheritance, and exports with source spans.
- [x] Emit symbol-level calls, state reads/writes, implements, overrides, callback registration, API exposure/consumption, and async-await relationships where statically resolvable.
- [x] Resolve local methods first, then typed fields/imported symbols, and skip ambiguous targets.
- [x] Emit explicit unresolved/ambiguous gaps rather than low-quality edges.
- [x] Keep es2panda/compiler integration behind the adapter boundary for a future exact provider.

Acceptance:

- No regex-derived relation is labelled exact.
- Symbol-level edges retain source location and adapter provenance.
- Existing file-level edges remain compatible fallbacks.

## Phase 4: Code Graph and Impact Integration

- [x] Persist normalized semantic relations into active `memory_edges` rows.
- [x] Expose qualified symbol names, signatures, spans, and evidence class in architecture slices.
- [x] Include semantic dependency relations in bounded design and impact traversal.
- [x] Prefer exact/static semantic edges over heuristic file-level duplicates.
- [x] Preserve existing graph depth, node, edge, and payload limits.

Acceptance:

- Design slices can show method-to-method and method-to-state paths.
- Impact analysis can recover symbol-level reverse consumers without widening global query traversal.
- Existing FTS5/query latency path is unchanged.

## Phase 5: Incident Causal Integration

- [x] Resolve matched code-log statements to their enclosing semantic symbol.
- [x] Build depth-bounded semantic candidate paths from calls, state, event, route/config, async, and API relations.
- [x] Label each step `observed`, `supports`, `possible`, or `inferred` independently of evidence class.
- [x] Persist only a compact structured causal chain and semantic target links, never raw logs or chain-of-thought.
- [x] Return semantic inspection targets and explicit chain gaps to the LLM.

Acceptance:

- A runtime log anchor is never presented as proof of every downstream static edge.
- Incident output distinguishes observed runtime facts from possible static paths.
- Existing string candidate-chain consumers remain backward compatible.

## Phase 6: Second Language Contract Proof

- [x] Implement a TypeScript adapter through the same semantic protocol.
- [x] Share only language-neutral ECMAScript parsing utilities; keep language capability declarations separate.
- [x] Add adapter conformance tests for deterministic keys, capabilities, ambiguity handling, and bounds.
- [x] Confirm graph and Incident consumers require no language-specific branches.

Acceptance:

- ArkTS and TypeScript batches validate through the same contract.
- Adding another adapter requires registration, not graph/storage/Incident changes.

## Phase 7: Evaluation, Documentation, and Release Gate

- [x] Add focused ArkTS/TypeScript semantic, incremental refresh, graph, impact, and Incident tests.
- [x] Measure resolved relations, skipped ambiguities, semantic edge growth, chain evidence roles, and bounded payloads.
- [x] Update README, runtime, schema, code-wiki, Skill protocol, and `gitlog.md`.
- [x] Run focused and complete tests, compilation, diff checks, four-Skill check, and 500-line gate.

## Performance Guardrails

- Parse only files in the learned or reverse-dependent refresh scope.
- Resolve targets from the current batch and indexed SQLite symbol metadata; do not load the whole graph.
- Keep semantic Incident traversal at depth two and at most 16 edges per log anchor.
- Keep architecture slices at depth two, 80 nodes, and 160 edges.
- Prefer local semantic flow; cross-module data flow requires an explicit source/sink request in a later phase.

## Future Exact Adapter

An es2panda, language-server, or SCIP adapter may emit `exact` batches later. It must run out of process, declare toolchain/version/capabilities, include source digests, and pass the same adapter conformance suite. The core runtime must not link to version-specific compiler internals.

## Rollback

Remove semantic adapter invocation and the compact Incident causal-chain field. Existing code files, symbols, logs, file-level edges, design checks, impact analysis, and Incident string chains remain usable. Added nullable symbol columns require no destructive rollback.
