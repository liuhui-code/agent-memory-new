# Method-Owner Context Generalization

## Goal

Let an Agent describe behavior rather than a known symbol name and still receive
the callable that owns the relevant implementation, with a current source span.
Keep the runtime evidence-only: it supplies candidate methods and source context
but does not infer a root cause or choose a final call path for the Agent.

## Problem

The semantic index already persisted callable identities, signatures, spans, and
typed graph edges. A method body, however, was not searchable unless the query
also matched its name, file, generated summary, or a learned business field.
Queries such as "authorization results from the permission request" could
therefore miss a generic method named `execute` even when its body called
`requestPermissionsFromUser` and read `authResults`.

Appending body terms to the ordinary symbol summary is not acceptable. It lets
common implementation words enter the high-priority symbol FTS lane, changes
unrelated file aggregation, and makes class/field identity retrieval less
precise. The first implementation confirmed this risk by reducing the
development context gate from 150/150 to 148/150.

## Architecture

### Extraction

- The language-neutral semantic batch remains the authority for callable kind
  and source span.
- Source files are loaded once per bounded semantic batch, not once per symbol.
- Only `function` and `method` entities receive body evidence.
- Chained member access and call identifiers are split into normalized terms.
- Language keywords, query stop words, the callable name, numbers, and malformed
  terms are removed.
- Each callable is limited to 240 source lines and 36 unique evidence terms.
- A learning pass reads at most 1,000 distinct files for this enrichment.

### Storage

- `code_symbols.method_evidence` stores generated, source-derived evidence.
- `code_symbols.summary` remains identity-oriented and backward compatible.
- `code_method_fts` is a separate FTS5 table, maintained by SQLite triggers.
- The table is sparse: symbols with empty method evidence have no FTS row.
- Search rebuilds restore the sparse index from SQLite source-of-truth rows;
  graph rebuilds recompute method evidence idempotently from current source.

### Retrieval

- Normal file and symbol FTS lanes are unchanged.
- The method lane runs only when the query has at least two focus terms.
- An OR-prefix FTS lookup produces at most 24 method candidates.
- A candidate must have direct evidence for at least two distinct focus terms.
- Method evidence contributes score only when `method_body_fts` recalled that
  symbol. A normal symbol hit cannot gain rank from incidental body words.
- Existing freshness validation blocks changed or missing source before output.
- Returned owners reuse semantic line ranges and bounded current excerpts.

### Query Constraints

Explicit result exclusions such as `do not return ProductRecord` or
`不要返回 ArticleRecord` are must-not clauses rather than positive evidence. An
excluded compound identifier is decomposed: its business-domain stem (`product`,
`article`) remains available for recall, while generic role terms (`record`,
`entity`, `model`) are removed. This avoids graph noise without discarding the
only domain clue.

## Data And Cost Boundaries

- No vector database, graph database, daemon, or new user-facing command.
- SQLite remains the only source of truth; both FTS tables are derived indexes.
- No full-table `%LIKE%` fallback is introduced.
- Empty symbols do not amplify method FTS storage at project scale.
- Query work is bounded by existing limits plus 24 method row IDs.
- Extraction work is proportional to learned callable spans, not archive history.

## Verification Plan

1. Learn an independent ArkTS fixture with unrelated sibling callables.
2. Prove evidence terms remain inside their owning callable span.
3. Prove a behavior query recalls the generic owner and source range.
4. Prove one-term method noise is rejected and the FTS index is sparse.
5. Prove repeated graph-derived rebuilds preserve method evidence.
6. Run focused semantic, recall, ranking, and graph performance tests.
7. Run all 54 development scenarios and 162 query variants.
8. Run 100,000-entity CI and 1,000,000-entity release scale gates.
9. Run full test discovery, compile, JSON, whitespace, and 500-line checks.

## Result

- The frozen pre-change commit reproduced 149/150 context cases; its existing
  failure treated a must-not identifier as positive expanded evidence.
- Isolated method evidence and explicit-exclusion decomposition produced 150/150
  passing variants across all 50 development scenarios.
- Average compact-context query time was 441.1 ms during the full capability run.
- CI scale passed at 100,000 entities and 300,000 edges; candidate-hit p95 was
  10.1 ms and the 500-method refresh was 554.6 ms.
- Release scale passed at 1,000,000 entities and 3,000,000 edges with a 2.064 GiB
  database. Candidate-hit p95 was 69.4 ms, the 20-method refresh was 419.9 ms,
  and the 500-method refresh was 1,681.3 ms.
- The database remained below the previous 2.113 GiB million baseline, confirming
  that empty method evidence did not create large FTS amplification.

### Independent Boundary Reproduction

- Four new project-neutral scenarios cover idempotent resource release,
  source-replacement state, prepared-command eligibility, and implementation
  ownership over examples. Each has three independent query variants.
- Method recall now uses bounded raw query terms and promotes a method owner
  only when at least three direct body-evidence terms agree. Strong exact,
  multi-concept, flow, or structural competitors prevent premature focus.
- Explicit `do not return sample/example/demo` roles are filtered before final
  code selection without treating ordinary files as examples.
- The expanded development gate passes 162/162 variants across 54 scenarios.

### Fourteenth-Project Observation

- Four real fixes from a previously unseen Wake-HarmonyOS revision history were
  reviewed at their full pre-fix revisions and sealed with digest
  `0ca1a2810280a686a77587c8e98c884c373ffbf6c4e85e17aa9aa08a43612873`.
- The sealed Context pack was executed exactly once and passed 1/4. The
  cross-page import completion/return chain passed; direct command ownership
  retained excess neighbors, visual-state ownership missed its method window,
  and the network-to-UI error contract missed both implementation owners.
- Agent A/B remains blocked because the Context gate failed. The sealed pack is
  consumed and cannot be rerun or used for tuning.
- The next repair must reproduce command-owner precision, visual-state passage
  focus, and cross-layer error-contract recall in independent fixtures. No
  project name, path, task wording, threshold, or Oracle from the sealed pack
  may enter retrieval logic.

## Rollback Boundary

Remove `method_evidence`, `code_method_fts`, its recall lane, and semantic body
extraction together. Keep must-not query decomposition independently because it
repairs a reproduced pre-existing precision defect and is not coupled to method
storage.

## Independent Wake Failure Reproduction

- Added three project-neutral scenarios with nine wording variants for UI
  command binding, comparison-target visual state, and service-to-UI error
  contracts.
- Added conservative executable-syntax markers for object callback bindings,
  disclosure rotation/toggle ownership, caught-error return boundaries, and UI
  error presentation boundaries.
- Separated comparison clauses and result exclusions from positive evidence.
  `instead of` remains problem evidence because it often describes faulty
  behavior rather than a result exclusion.
- Kept semantic path expansion for bounded graph lineage, but restricted the
  high-weight path-identity bonus to direct user terms.
- Kept the three-term method focus boundary. A two-term method can focus only
  for an explicit lowerCamelCase member, method-FTS and direct-path evidence,
  and a two-times score lead over the next direct candidate.
- The development gate passes 171/171 variants across 57 scenarios. Anchor
  recall is 1.0, MRR is 0.9938, source-span recall is 1.0, and average compact
  context is 720.2281 Tokens.

## Fifteenth-Project Observation

- Four source-reviewed RayTV fixes were sealed with digest
  `589240f57caefbf641a803e859a51635dd4dd0080f854bd412aa055c0d198a3f`.
- The pack was executed exactly once and passed 0/4. Every expected file was
  recalled, but generated preview output, alternate Python implementations,
  and same-domain repository/service neighbors reduced precision to 0.2708.
- None of the four audited callable spans was returned. Aggregate anchor recall
  is 1.0, primary-anchor recall is 0.75, MRR is 0.4791, and source-span recall
  is 0.0.
- Agent A/B remains blocked. This pack is consumed and must not be rerun or used
  for tuning.

## Post-RayTV Independent Reproduction

- Added four project-neutral scenarios with twelve wording variants for
  canonical source over generated previews, explicit implementation-language
  preference, complete UI mechanism ownership over same-domain neighbors, and
  a callable window near the end of a 500-line ArkTS file.
- Added one bounded source-path policy shared by learning and query selection.
  Known preview/cache/generated directories are skipped during learning;
  existing archives retain generated candidates only as a fallback when no
  canonical candidate exists.
- Explicit query language is resolved through a small language-to-suffix
  registry. Filtering activates only when one positive language is named and
  falls back when no matching candidate exists.
- Added a guarded asynchronous action concept requiring conditional branch,
  state-write, and async-boundary evidence. This prefers a complete UI owner
  without suppressing legitimate component flows or cross-layer owners.
- Added `omit` and `omitting` to result-exclusion decomposition. Large-file
  excerpts continue to use stored callable ranges and the existing 40-line
  cap; no larger file prefix is returned.
- The expanded development gate passes 183/183 variants across 61 scenarios.
  Anchor recall and source-span recall are 1.0, Oracle precision is 0.9478, MRR
  is 0.9943, and average compact context is 722.2951 Tokens.
- CI scale passes at 100,000 searchable entities and 300,000 edges. Candidate
  hit p95 is 10.02 ms and the 500-method refresh p95 is 578.846 ms.
- RayTV remains a consumed observation and was not rerun. Promotion remains
  denied until a new independent sealed project passes Context before Agent
  A/B.

## Sixteenth-Project Observation

- Three real FlameChase fixes were reviewed at complete immutable pre-fix
  revisions: custom-dialog close ownership, award preference-key restoration,
  and ArkUI-X platform gating for the dark-mode control.
- The MPL-2.0 ArkTS pack was sealed with digest
  `51784c6b80b0b0baf68e85136cec638f4351a0ea8f8325319165b9007dbe965c`
  and executed exactly once. It passed 0/3.
- Award restoration and platform gating recalled their expected files, but the
  former missed its audited lifecycle passage and retained a presentation
  neighbor while the latter retained three unrelated neighbors. Dialog close
  ownership was absent from candidate generation.
- Aggregate anchor recall is 0.6667, Oracle precision is 0.25, MRR is 0.3333,
  source-span recall is 0.3333, and average compact context is 1,109.3333
  Tokens. Agent A/B was not run.
- This pack is consumed and must not be rerun or used for tuning. Future repair
  requires project-neutral reproductions before another independent sealed
  observation.

## Post-FlameChase Independent Repair

- Added three project-neutral development scenarios with nine wording variants
  for indirect dialog caller ownership, persistence-key restore ownership, and
  platform-sensitive UI ownership. Their first baseline passed 2/9.
- Added structural ArkTS contracts for actual UI callback bindings,
  persistence reads with literal keys, and platform-sensitive UI controls.
- Added an opt-in, one-hop reverse caller expansion. It activates only for
  explicit caller/owner intent, starts from a bounded set of indirect roles,
  requires a semantic call edge and UI callback evidence, and returns at most
  two owners. It does not expand default graph depth or globally enable call
  neighbors.
- Contract-complete owners are focused before generic method evidence. This
  keeps lifecycle presentation files and same-domain neighbors from displacing
  the source that owns the requested persistence or platform mechanism.
- The three new scenarios pass 9/9 and seven related regression scenarios pass
  21/21. The complete development gate passes 192/192 variants across 64
  scenarios with anchor recall 1.0, Oracle precision 0.9504, MRR 0.9945,
  source-span recall 1.0, and 721.5365 average context Tokens.
- Full discovery ran 646 tests. The restricted sandbox passed all tests except
  two loopback-bind cases; the complete loopback test module passed 3/3 when
  local port binding was permitted. Compile, whitespace, JSON, and the Python
  500-line gate pass.
- CI scale passes at 100,000 searchable entities, 80,000 symbols, and 300,000
  graph edges. Candidate hit/miss p95 is 10.632/19.334 ms, single-file refresh
  p95 is 223.003 ms, and the 500-method refresh p95 is 621.899 ms.
- No consumed sealed pack was rerun or modified. Promotion remains denied. The
  only valid next observation is a newly reviewed and sealed external project.

## Seventeenth-Project Observation

- Selected the previously unseen MIT-licensed LinysBrowser_NEXT ArkTS browser
  after reviewing its complete Git history and 207 ArkTS/TypeScript files.
- Reviewed three source-provable fixes at complete pre-fix revisions: location
  permission dialog cancellation, non-2-in-1 bottom avoid layout, and oversized
  saved WebState rejection.
- Git revision audit verified all expected changed files. The three-case pack
  was sealed with digest
  `7b337f701b4545df9abec518af691936dee2264510cc799e6342791b41826ea3`
  and executed exactly once.
- The Context gate passed 0/3. The location owner was recalled at rank 4 behind
  generic dialog infrastructure; the platform layout owner and saved-state
  restore owner were absent from candidate generation.
- Aggregate anchor recall is 0.3333, primary recall is 0, Oracle precision is
  0.0833, MRR is 0.0833, and source excerpt/span recall is 0. Average compact
  context is 1,134 Tokens and average query time is 1,000 ms.
- Agent A/B was not run. The sealed inventory is 17 projects and 72 cases, and
  promotion remains denied.
- This pack is consumed and must not be rerun or used for tuning. Future repair
  must reproduce only the abstract failure classes in unrelated fixtures and
  validate them on another new sealed project.
