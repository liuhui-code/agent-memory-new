# Multi-Stage Retrieval Architecture Plan

## Goal

Evolve Context retrieval from one mixed scoring path into a bounded,
inspectable multi-stage retrieval system that generalizes across projects.
Keep `context` as the only diagnosis handoff, SQLite as the source of truth,
and the existing four user-facing Skills.

This is an architectural program, not a repair for any consumed holdout. No
project name, path, identifier, task phrase, Oracle threshold, or result from a
sealed pack may become a retrieval rule or tuning feature.

## Mature Basis

- [BEIR](https://arxiv.org/abs/2104.08663) shows that BM25 remains a strong
  zero-shot baseline and that candidate retrieval followed by reranking is a
  robust cross-domain pattern.
- [Reciprocal Rank Fusion](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)
  combines independent rankings without assuming their raw scores are
  comparable.
- [Agentless](https://arxiv.org/abs/2407.01489) localizes repository work from
  files to functions and then lines instead of selecting final passages in one
  global step.
- [GraphRAG local search](https://microsoft.github.io/graphrag/query/local_search/)
  uses retrieved entities as bounded graph entry points, combines structured
  relationships with source text, and filters the result to a context budget.
- [SQLite FTS5](https://www.sqlite.org/fts5.html) supports BM25 column weights,
  allowing fielded lexical retrieval without adding another database.

The project adopts these retrieval principles, not their storage stacks or LLM
reasoning components.

## Stable Boundaries

User-facing flow remains:

```text
agent-memory-query
  -> tools/agent_memory.py context
  -> compact evidence context
  -> local Agent diagnosis and verification
```

Internal flow becomes:

```text
QueryIntent
  -> CandidateRetriever[]
  -> RankFusion
  -> OwnerReranker
  -> HierarchicalEvidenceSelector
  -> ContextBudget
```

The Runtime retrieves and explains evidence. It does not infer a root cause,
choose a repair, parse temporary user logs, or persist Agent reasoning.

## Interfaces

### QueryIntent

A deterministic description of positive query facets:

- explicit identifiers and paths
- domain/entity terms
- operation and lifecycle terms
- UI, platform, persistence, log, and failure constraints
- negative clauses and result-role exclusions

It must not contain a project-specific synonym table learned from a holdout.

### CandidateRetriever

Each retriever returns a bounded ranked list with a stable channel name:

- file/path lexical retrieval
- symbol/signature lexical retrieval
- callable/body passage retrieval
- structural contract retrieval
- log-template retrieval
- experience retrieval
- seed-bounded graph expansion

Raw scores remain channel-local and are never compared across retrievers.

### RankFusion

Combines ranked lists into candidates with:

- fused score
- best source rank
- contributing channels
- per-channel contribution

The first implementation is weighted RRF. Weights describe channel reliability,
not task cases, projects, or file roles. The implementation stays replaceable
behind a protocol.

### OwnerReranker

Reranks only the bounded fused set using inspectable features:

- exact identity and path evidence
- query facet coverage
- complete mechanism ownership
- source-locatable callable evidence
- supported graph relation and distance
- generic infrastructure or generated-source penalties

It must not repair absent candidates. Candidate recall and reranking remain
separately measured.

### HierarchicalEvidenceSelector

Selects evidence in three stages:

1. file
2. callable/symbol
3. source line window

Source windows must be query-supported callable or expression ranges, never a
larger arbitrary file prefix.

## Phases

### Phase 1: Rank Fusion Contract

- Add a storage-neutral `RankFusionPort`.
- Implement weighted RRF over existing FTS recall lanes.
- Preserve bounded candidate limits and freshness filtering.
- Attach fusion provenance to each returned candidate and query audit.
- Keep the current scorer and owner focus as the downstream reranker.

Acceptance:

- a candidate supported by independent channels outranks a single-channel
  candidate with a similar source rank;
- weak method-body fallback cannot crowd out identity/structural channels;
- results are deterministic under stable input ordering;
- existing development Context gate does not regress;
- scale SLO and SQL query-plan gates remain passing.

### Phase 2: Fielded Passage Retrieval

- Treat files, symbols, and callable bodies as distinct retrievers.
- Apply explicit FTS5 column weights for path, symbol, business semantics,
  structural markers, and method evidence.
- Normalize CamelCase, snake_case, API property chains, and string-key evidence
  during indexing.
- Measure candidate Recall@20 before any owner reranking.

No vector database is required. Passage rows remain source-derived SQLite data
bound to file digest and index generation.

### Phase 3: Language Semantic Adapters

- Extend the language-neutral adapter contract with expression-level operations,
  guards, resource bounds, callback ownership, platform predicates, and
  persistence read/write chains.
- Keep ArkTS extraction behind the adapter registry.
- Require project-neutral fixtures for every semantic contract.
- Add other languages through the same normalized contract, not query forks.

### Phase 4: Hierarchical Localization

- Select files from fused retrieval.
- Select callables only inside those files or supported one-hop graph owners.
- Select compact source ranges from callable and expression evidence.
- Preserve path diversity when multiple causal routes remain plausible.

### Phase 5: Cross-Project Calibration

- Use leave-one-project-out development evaluation.
- Track Recall@20 for candidate generation independently from Precision@3, MRR,
  and source-span recall.
- Use sealed projects exactly once and never feed their observations back into
  thresholds or rules.
- Run Agent A/B only after a new sealed Context pack passes.

## Performance Budget

- Every retriever has an explicit top-N limit.
- Fusion is in-memory over bounded integer IDs and is linear in returned ranks.
- Graph expansion remains relation-specific and at most one hop unless a future
  reviewed architecture decision changes the bound.
- Query performs no full repository scan and no large-table `%LIKE%` fallback.
- Million-entity SLO and expected SQLite indexes remain release gates.

## Governance

Every failed external observation must identify one owning layer:

- query intent
- candidate retrieval
- rank fusion
- owner reranking
- graph expansion
- passage selection
- context budgeting

Repairs are developed on unrelated fixtures at that layer. A consumed holdout
may explain a failure class, but it cannot supply implementation constants,
test wording, identifiers, or promotion evidence.

## Rollback

Each phase is independently removable:

- Phase 1 can restore deterministic lane concatenation behind `RankFusionPort`.
- Passage and semantic indexes are derived data and can be rebuilt from source.
- No phase changes durable experience, user-facing Skills, or the `context`
  command contract.

## Phase 1 Completion

Completed on 2026-07-20:

- Added the storage-neutral `RankFusionPort` and deterministic weighted RRF.
- Preserved the existing SQLite FTS5 channels, limits, freshness checks, and
  downstream owner reranker.
- Added per-candidate fusion provenance to full query results and audit without
  increasing compact-context output.
- Kept channel-local BM25 scores isolated; only bounded ranks cross the fusion
  boundary.
- Added project-neutral contract, compatibility, and audit regression tests.

Verification:

- Complete development Context gate: 192/192 variants across 64/64 scenarios,
  anchor recall 1.0, MRR 0.9945, source-span recall 1.0, average compact context
  721.5365 Tokens.
- CI scale gate: 100,000 entities, 80,000 symbols, and 300,000 graph edges pass;
  candidate hit/miss p95 is 10.226/17.61 ms and 500-method refresh p95 is
  592.658 ms.
- Full unit discovery: 650 tests; only two expected loopback bind failures in
  the restricted sandbox, with their complete module passing 3/3 when loopback
  binding is permitted.
- All Python source and test files remain at or below 500 lines.

No consumed sealed pack was rerun or changed. Phase 1 therefore establishes the
fusion architecture and development compatibility only; it is not evidence
that the LinysBrowser or other external failures are repaired. Phase 2 remains
fielded passage retrieval and independently measured candidate Recall@20.

## Phase 2 Completion

Completed on 2026-07-20:

- Added rebuildable `code_passages` for file, symbol, and callable units, bound
  to source digest and atomic index generation.
- Kept path/symbol identity, business and structural semantics, bounded method
  evidence, and string-key evidence in separate searchable fields.
- Added six independently weighted SQLite FTS5 retrievers and a nested RRF
  boundary whose output can be measured without changing serving candidates.
- Added project-neutral passage generation, scoped replacement, channel weight,
  string-key, fusion audit, and end-to-end learning tests.
- Added candidate file Recall@20 to deterministic capability evaluation,
  independently from owner MRR, final precision, and source-span recall.

An initial development experiment connected the expanded fielded candidates
directly to the existing owner reranker. It regressed 5 of 192 known variants:
correlated field channels expanded recall, but the downstream scorer was not
calibrated for the larger candidate distribution. The implementation therefore
uses a production-style shadow deployment. Full Context can audit fielded
results, compact Context keeps the Phase 1 serving path and budget, and the
release surface does not silently absorb an unproven candidate set.

Verification:

- Complete development Context gate: 192/192 variants and 64/64 scenarios pass;
  anchor recall 1.0, Oracle precision 0.9504, MRR 0.9945, source-span recall
  1.0, and average compact context 721.5365 Tokens.
- Shadow fielded candidate file Recall@20 is 0.8925. This is below promotion
  quality and remains an explicit development metric rather than a gate pass.
- CI scale gate passes at 100,000 entities, 80,000 symbols, and 300,000 graph
  edges. Candidate hit/miss p95 is 30.514/55.063 ms; no-change, outside-Scope,
  single-file, and 500-method refresh p95 is 210.648/216.891/525.037/2,127.179 ms.
- Full unit discovery ran 656 tests. The restricted sandbox had only two
  expected loopback-bind errors; the complete loopback module passed 3/3 where
  binding was allowed. All Python source and test files remain within 500 lines.

No consumed sealed pack was rerun or changed. Phase 3 must first improve
language-neutral passage recall and add semantic-adapter contracts on unrelated
fixtures. Fielded serving promotion then requires candidate-recall, owner
reranker, regression, scale, and one new sealed-project gate to pass together.

## Phase 3 Completion

Completed on 2026-07-21:

- Extended `semantic-index/v1` with optional, bounded `SemanticMechanism`
  records while preserving compatibility with existing provider payloads.
- Upgraded the built-in ArkTS and TypeScript static adapters to `1.1` and kept
  language-specific extraction behind the existing adapter registry.
- Normalized operations, guards, resource bounds, callback bindings, platform
  predicates, and persistence reads/writes with source-symbol and line bounds.
- Persisted bounded mechanism JSON on `code_symbols` without source bodies and
  projected only normalized terms into a dedicated passage field.
- Upgraded the rebuildable search schema to `fts-v4` and added the independent
  `semantic_mechanism_fts` shadow lane. Legacy passage schemas are dropped and
  rebuilt from source rows; durable memory is untouched.

Verification:

- Complete development Context gate passes 192/192 variants and 64/64 scenarios;
  anchor recall 1.0, Oracle precision 0.9504, MRR 0.9945, source-span recall
  1.0, average compact context 721.5365 Tokens, average preparation 2,086.1771
  ms, and average compact query 631.1094 ms.
- Shadow candidate file Recall@20 improves from 0.8925 to 0.8980. This remains
  below promotion quality and does not change the serving candidate set.
- CI scale passes at 100,000 entities, 80,000 symbols, and 300,000 edges.
  Candidate hit/miss p95 is 10.956/20.271 ms; no-change, outside-Scope,
  single-file, and 500-method refresh p95 is 90.504/131.014/227.843/812.501 ms.
- Query tests pass 62/62, Context tests 40/40, and focused semantic/passage tests
  33/33. Full discovery runs 660 tests; only two restricted-sandbox loopback
  errors remain, with the complete loopback module passing 3/3 when allowed.

No consumed sealed pack was rerun or changed. Phase 3 establishes attributable
semantic candidate evidence, not external generalization. Phase 4 will perform
hierarchical file-to-callable localization and owner-reranker calibration while
keeping all fielded channels in shadow until the complete promotion gates pass.
