# Real-Project Capability Validation Loop

**Goal:** Prove that Agent Memory supplies useful, compact context on unseen ArkTS repository tasks and improves an external Agent without hiding quality or cost regressions.

**Architecture:** Keep the four public skills and `tools/agent_memory.py` facade. Add evaluation-only case sealing and failure attribution beside the existing Context and Agent evaluators. SQLite remains the runtime source of truth; sealed JSON packs and compact reports are test artifacts.

## Non-Negotiable Boundaries

- Runtime retrieves and compresses evidence; the Agent owns diagnosis and design reasoning.
- A sealed holdout is executed once and is never used for ranking, threshold, or mutation tuning.
- A failed holdout creates a failure classification, not a direct production weight change.
- Reproduce failures in an independent development fixture before changing implementation.
- Context quality and Agent outcome are separate gates.
- Promotion requires both Agent quality and efficiency gates.
- No fifth skill, daemon, vector database, graph database, or new public diagnosis facade.
- Every Python source and test file remains at or below 500 lines.

## Method Foundations

| Method | Project application | Primary reference |
|---|---|---|
| Reusable test collections | Separate development and final evaluation packs | NIST TREC, https://trec.nist.gov/howto.html |
| Real repository tasks | Use issue/fix history and the pre-fix revision | SWE-bench, https://arxiv.org/abs/2310.06770 |
| Out-of-domain retrieval | Require a second ArkTS repository and wording variants | BEIR, https://arxiv.org/abs/2104.08663 |
| Local graph retrieval | Expand only bounded neighbors of query-matched entities | GraphRAG Local Search, https://microsoft.github.io/graphrag/query/overview/ |
| Multi-stage retrieval | Diagnose candidate generation separately from ranking | TREC-style ranked retrieval evaluation |
| Evidence calibration | Keep association, structural support, runtime observation, and verification distinct | Project causal evidence contract |
| Cost-aware promotion | Require quality and efficiency rather than answer quality alone | Existing Agent benchmark quality/efficiency split |

## Case Lifecycle

```text
draft
  -> source-reviewed
  -> validated on the pre-fix revision
  -> assigned to development or holdout
  -> sealed with canonical SHA-256
  -> context-only run
  -> eligible Agent A/B run
  -> retained unchanged as an observation
```

Every sealed case records:

- repository and immutable pre-fix revision;
- task wording available to the Agent;
- hidden post-fix revision and commit message;
- expected and forbidden files;
- expected source spans;
- optional log, experience, and bounded path requirements;
- verification evidence;
- review status and explicit hidden-field policy.

The seal digest covers the complete pack except the seal object itself. A modified sealed pack must fail before source preparation or Agent invocation.

## Two-Level Gate

### Gate 1: Context Supply

Run the deterministic compact-context evaluator first. Measure:

- expected anchor recall and primary-anchor recall;
- Top-K precision and MRR;
- source excerpt and source-span recall;
- log emitter, experience-lane, relation, and path requirements when declared;
- forbidden evidence absence;
- no-evidence abstention;
- query wording robustness;
- context Token budget and query latency.

Only cases passing this gate may support an Agent-uplift claim. A failed context case is classified before any implementation work.

### Gate 2: Agent A/B

For each eligible case run three paired trials:

- Baseline: frozen source plus normal local source tools.
- Memory: identical source, Agent, prompt, and limits plus the existing Query Skill context.

Measure root-cause category, expected-file recall, forbidden direction, causal calibration, verification, stability, Token cost, elapsed time, source searches, source reads, and read amplification. Promotion requires quality and efficiency gates to pass together.

## Failure Attribution Contract

| Failure class | Layer | Permitted repair | Prohibited shortcut |
|---|---|---|---|
| `candidate_generation` | lexical/index/adapter | Improve missing extraction or bounded recall | Boost an absent candidate in final ranking |
| `ranking_precision` | rank/fusion | Improve field evidence, reranking, or diversity | Unbounded graph expansion |
| `passage_selection` | source window | Query-focused symbol or line selection | Return a larger arbitrary file prefix |
| `graph_structure` | semantic graph | Add evidence-backed language-neutral relations | Treat text similarity as a call edge |
| `experience_governance` | memory lanes | Scope, freshness, conflict, or guard correction | Prefer newest or most similar blindly |
| `abstention_calibration` | output contract | Expose missing evidence and lower confidence | Fill an empty lane with weak matches |
| `context_compactness` | projection | Remove redundant evidence after preserving anchors | Drop required evidence to meet budget |
| `agent_protocol` | Skill/runner | Improve query iteration or stop protocol | Modify retrieval when context is already correct |
| `agent_efficiency` | runner/context use | Reduce repeated searches and reads | Relax cost limits after observing results |

Each failed report must include the failed check, failure class, owning layer, method reference, allowed repair boundary, prohibited shortcut, and next validation step.

## Execution Phases

### Phase 1: Seal And Leakage Guard

- Add a canonical pack digest and seal schema.
- Validate review status, pre/post revisions, hidden Oracle fields, and source-review evidence.
- Add an evaluation-only seal command through the existing runtime facade.
- Reject modified or incompletely reviewed sealed packs before evaluation.

### Phase 2: Theory-Grounded Failure Reports

- Classify failed Context checks without changing scoring.
- Classify Agent quality and efficiency failures separately.
- Persist compact failure summaries in existing runtime snapshots.
- Surface the primary failure class through maintain health.

### Phase 3: Real Case Packs

- Retain the three existing Gramony packs as immutable observations.
- Collect new development cases from unseen Gramony history without reading old holdout Oracles during tuning.
- Collect cases from a second ArkTS repository.
- Review tasks and source diffs, then seal at least 12 holdout cases across repositories.
- Include diagnosis, path-disambiguation, design-context, and abstention coverage where supported by the evaluator.

### Phase 4: Context Repair Loop

- Execute the Context gate once on a sealed pack.
- Classify failures.
- Reproduce only the leading failure class in independent development fixtures.
- Apply the smallest layer-correct repair.
- Run focused tests, the 36-variant development gate, and the full suite.
- Use a new sealed pack for the next generalization observation.

### Phase 5: Agent A/B And Release Decision

- Run three paired trials only after Context eligibility.
- Preserve response metadata but not chain-of-thought or raw temporary logs.
- Require complete cost attribution.
- Produce one compact release decision with quality, efficiency, generalization, and audit status.

## Completion Criteria

- At least 12 source-reviewed, sealed, real ArkTS cases from two repositories.
- Seal tampering and Oracle leakage tests pass.
- Every Context and Agent failure has a theory-grounded classification.
- Context report exposes cross-project aggregate metrics and abstention.
- Agent A/B uses three paired trials with complete quality and cost accounting.
- Promotion is denied unless both gates pass.
- Existing four skills and the runtime boundary remain unchanged.
- Full test suite passes and every code file is at most 500 lines.
- `gitlog.md` and user documentation describe the workflow and limitations.

## 2026-07-18 Large-Repository Retrieval Iteration

- [x] Extract SQLite candidate generation from the 500-line collection module
  behind a replaceable `CandidateRecallPort`.
- [x] Add bounded broad, conjunctive, and per-concept FTS5 lanes. Extra lanes
  activate only after broad recall saturates.
- [x] Expose candidate and post-ranking stage counts through full query audit
  without adding fields to compact Agent context.
- [x] Add query-focus coverage reranking and suppress generic `content` path
  identity boosts.
- [x] Prefer evidence-backed symbol ranges before whole-file passage fallback.
- [x] Add independent noisy large-repository fixtures for complementary owner
  recall, ranking, passage selection, audit boundaries, and port replacement.
- [x] Keep the 15-scenario/45-variant development gate passing, then execute
  the two reserved Gramony cases exactly once.

The consumed Gramony observation passes 0/2. It improves aggregate anchor
recall and MRR to 0.75 but fails precision and source-span gates. Promotion
remains denied. Further repairs require new independent fixtures and a newly
sealed external project; these two cases cannot be rerun for tuning.

## 2026-07-19 Third-Project Generalization Observation

- [x] Reproduce late-owner recall, dominant-owner diversity, executable passage
  focus, and tight three-anchor source budgeting in independent fixtures.
- [x] Restore the 15-scenario/45-variant development gate under the existing
  1,500-Token compact-context ceiling.
- [x] Review three real Bookkeep fixes at immutable pre/post revisions and seal
  the complete pack after changed-file and leakage audits.
- [x] Execute the sealed pack exactly once and retain a compact immutable result.
- [x] Keep promotion denied and record the next repair at the candidate-recall
  boundary rather than tuning the consumed tasks.

The Bookkeep observation passes 0/3 with no returned code anchors. Report-level
failures include ranking and passage checks, but their shared root is candidate
generation across an abstract English symptom, Chinese business vocabulary,
generic page names, and ArkTS modifier syntax. The pack is consumed and cannot
be rerun. The next iteration must add independent multilingual/structural
development cases, then use a fourth sealed project for external validation.

## 2026-07-19 Structural Recall And Fourth-Project Observation

- [x] Add independent abstract symptom fixtures for scrolling, reactive
  aggregate refresh, and visual overlap without copying external project names.
- [x] Add a bounded, language-neutral structural FTS lane behind the existing
  candidate recall abstraction and expose its audit count only in full output.
- [x] Rank structural candidates by actual indexed marker coverage and index
  ArkTS `forEach` behavior without creating causal edges.
- [x] Preserve alternate causal paths before redundant non-emitter excerpts
  under the existing 1,500-Token compact budget.
- [x] Expand the development gate to 18 scenarios and 54 wording variants;
  retain a 54/54 pass before external observation.
- [x] Review, seal, and execute four Home Assistant cases exactly once; retain
  the failed result and keep promotion denied.

The fourth-project observation passes 0/4. Structural recall finds the reusable
layout owner at rank one but returns two excess neighboring pages. Three other
cases miss lifecycle, callback-containment, and authoritative-refresh owners.
The sealed pack is consumed. The next repair loop must use independent fixtures
and a new sealed pack; no Home Assistant query, threshold, or Oracle may be
changed for tuning.

## 2026-07-19 Mechanism Recall And Fifth-Project Observation

- [x] Add independent reusable-spacing, fallback-recovery,
  callback-containment, and post-action-refresh fixtures with three wording
  variants each.
- [x] Extract bounded ArkTS existing-mechanism markers without inferring absent
  behavior, and keep a minimal complementary owner cover.
- [x] Make exact high-entropy identifier queries abstain unless direct or
  graph-supported evidence exists.
- [x] Make the full development pack the default Context evaluation scope and
  retain a 66/66 pass across 22 scenarios.
- [x] Review and seal four real Aigis fixes, execute the pack exactly once, and
  retain the immutable failed observation.
- [x] Keep promotion denied and move the next repair to independent
  event/state/persistence development fixtures.

The fifth-project observation passes 1/4. TOTP default construction passes;
two UI state/validation owners are recalled with excess neighbors, and the OTP
usage persistence owner is absent. The pack is consumed and cannot be rerun.
No Aigis-specific name, phrase, threshold, or Oracle may enter retrieval code.

## 2026-07-19 Event/Persistence Recall And Sixth-Project Observation

- [x] Reproduce event-to-state handoff, validation-stop ownership,
  persistence writes, paired counter/timestamp commits, and combined-owner
  precision in independent fixtures with three wording variants each.
- [x] Add conservative ArkTS mechanism extraction and language-neutral query
  concepts without project-specific names or inferred missing repairs.
- [x] Preserve direct structural ownership when graph provenance is also
  present, while keeping unsupported graph neighbors bounded.
- [x] Expand the development gate to 26 scenarios and 78 variants and retain a
  78/78 pass before external observation.
- [x] Review, seal, and execute four harmonyos-games cases exactly once; retain
  the immutable failed observation.
- [x] Keep promotion denied and move the next repair to independent abstract
  gesture-to-state recall and excess-neighbor precision fixtures.

The sixth-project observation passes 1/4. One context owner passes exactly;
two mutation/lifecycle owners rank first but fail precision, and one gesture
state owner is absent. The pack is consumed and cannot be rerun. No repository
name, path, task phrase, threshold, or Oracle from this pack may enter tuning.

## 2026-07-19 Gesture Precision And Seventh-Project Observation

- [x] Reproduce abstract gesture ownership, adjacent collection mutation, and
  lifecycle-persistence precision in independent fixtures with three wording
  variants each.
- [x] Add conservative gesture-boundary and indexed-collection-write markers;
  recognize restore as a lifecycle operation without changing global scores.
- [x] Retain only the complete multi-mechanism owner when partial neighbors add
  no missing structural evidence.
- [x] Expand the development gate to 29 scenarios and 87 variants and retain an
  87/87 pass before external observation.
- [x] Review four single-owner JustPDF fixes, seal the source-audited pack, and
  execute it exactly once.
- [x] Keep promotion denied and move the next repair to independent async owner
  recall, touch-arbitration precision, and method-level passage fixtures.

The seventh-project observation passes 1/4. Empty launch-value handling passes;
one touch owner is noisy and its handler window is missed, one rapid-navigation
owner is absent, and one correctly ranked save owner has the wrong method
window. The pack is consumed and cannot be rerun. No JustPDF name, path, task
phrase, threshold, or Oracle may enter retrieval tuning.

## 2026-07-19 Async/Method Focus And Eighth-Project Observation

- [x] Reproduce async state ordering, touch-state arbitration, and method-level
  passage focus in independent fixtures with three wording variants each.
- [x] Prefer complete multi-mechanism evidence over generic operation names
  while retaining explicit code identity precedence.
- [x] Use word-aware English concept triggers and preserve mechanism-backed
  ECMA callable ranges before lexical passage fallback.
- [x] Read each source file once during range selection and retain the 1,500
  Token compact-context ceiling.
- [x] Expand the development gate to 31 scenarios and 93 variants and retain a
  93/93 pass before external observation.
- [x] Review and seal four FinVideo fixes, execute the pack exactly once, and
  retain the immutable failed observation.

The eighth-project observation passes 0/4. Three expected owners are recalled,
but nested ArkUI callback and Builder windows remain weak and two cases retain
excess neighbors. Conditional folder-list loading misses its ViewModel owner.
The pack is consumed and cannot be rerun. Further repair requires independent
fixtures and a new sealed project; no FinVideo-specific name, path, task phrase,
threshold, or Oracle may enter tuning.

## 2026-07-19 ArkTS DSL Focus And Ninth-Project Observation

- [x] Reproduce nested touch callbacks, conditional collection loading,
  lifecycle callback cleanup, and Builder layout focus in independent fixtures
  with three wording variants each.
- [x] Add conservative ArkTS mechanism markers for indexed touch access,
  conditional data sources, cleanup boundaries, layout axes, and async ordering.
- [x] Add an ArkTS source-range adapter for chained arrow callbacks while
  retaining standard ECMA callable ranges and one source read per candidate.
- [x] Add bounded component identifier terms and raw-query-only explicit-path
  protection without allowing semantic, negative, or behavior queries to pin
  unrelated files.
- [x] Expand the development gate to 35 scenarios and 105 variants and retain a
  105/105 pass before external observation.
- [x] Review and seal four Wechat_HarmonyOS fixes, execute the pack exactly
  once, and retain the immutable failed observation.

The ninth-project observation passes 1/4. Status-bar ownership passes; audio
lifecycle retrieval is noisy and misses the audited method, reusable Toolbar
candidate generation fails, and search keyboard/back handling is recalled too
late with a mismatched source window. The pack is consumed and cannot be rerun.
Further repair requires independent fixtures and a new sealed project; no
Wechat_HarmonyOS name, path, task phrase, threshold, or Oracle may enter tuning.

## 2026-07-19 Role/Boundary Recall And Tenth-Project Observation

- [x] Reproduce reusable toolbar ownership, media resource shutdown, and
  keyboard/back event boundaries in independent fixtures with three wording
  variants each.
- [x] Add conservative ArkTS role and lifecycle markers without introducing
  project aliases or inferred repairs.
- [x] Keep a bounded structural recall lane available under broad FTS
  saturation and suppress expansion-only tails only under strong identities.
- [x] Preserve component-flow lineage and retain the existing compact-context
  budget and runtime boundary.
- [x] Expand the development gate to 38 scenarios and 114 variants and retain a
  114/114 pass before external observation.
- [x] Review and seal four Siyuan Harmony fixes, execute the pack exactly once,
  and retain the immutable failed observation.

The tenth-project observation passes 0/4. Three expected owners are recalled,
but all four audited source spans are missed and unrelated neighbors remain.
Archive extraction ownership is absent behind package metadata. The pack is
consumed and cannot be rerun. Further repair requires independent fixtures and
a new sealed project; no Siyuan name, path, task phrase, threshold, or Oracle
may enter tuning.

## 2026-07-19 I/O/Conversion Recall And Eleventh-Project Observation

- [x] Reproduce archive I/O, collection aggregation, keyboard focus state, and
  native color parsing in independent fixtures with three wording variants.
- [x] Add conservative ArkTS mechanism markers and query concepts without
  project aliases or inferred missing repairs.
- [x] Merge query-supported callable ranges ahead of stale stored ranges and
  retain nested ArkUI callback precision.
- [x] Remove generic shared/component terms from reusable-spacing structure
  evidence after an independent cross-concept regression.
- [x] Expand the development gate to 42 scenarios and 126 variants and retain
  a 126/126 pass before external observation.
- [x] Review and seal four Termony fixes, execute the pack exactly once, and
  retain the immutable failed observation.

The eleventh-project observation passes 1/4. Touch coordinate conversion and
its callback span pass. Empty-output scrolling finds its page but not the read
loop, while clipboard extraction and permission sequencing return module
metadata instead of ArkTS owners. The pack is consumed and cannot be rerun.
Further repair requires independent fixtures and a new sealed project; no
Termony name, path, task phrase, threshold, or Oracle may enter tuning.

## 2026-07-19 Behavior-Owner Recall And Twelfth-Project Observation

- [x] Reproduce clipboard content reads, sequential permission/result guards,
  process-output read loops, and runtime-capability probes in independent
  fixtures with three wording variants.
- [x] Add conservative ArkTS behavior markers and query concepts without
  project aliases or inferred missing repairs.
- [x] Strip explicit negative clauses before concept expansion and keep exact
  log retrieval unchanged.
- [x] Exclude generic identity-only log emitters from structural compact
  anchors when path reconstruction is inactive.
- [x] Prevent a later arrow expression from becoming the callback range of an
  already closed ArkTS call.
- [x] Expand the development gate to 46 scenarios and 138 variants and retain
  a 138/138 pass before external observation.
- [x] Review and seal four ClearChat fixes, execute the pack exactly once, and
  retain the immutable failed observation.

The twelfth-project observation passes 0/4. Cache ownership and its audited
span are found but broad search neighbors dominate precision. Streaming
ownership ranks second while both persistence windows are missed.
Initialization timeout and WebView security ownership are absent. The pack is
consumed and cannot be rerun. Further repair requires independent fixtures and
a new sealed project; no ClearChat name, path, task phrase, threshold, or
Oracle may enter tuning.

## 2026-07-19 Async/Security Mechanisms And Thirteenth-Project Observation

- [x] Reproduce serialized incremental/final writes, timeout cancellation,
  WebView navigation policy, and bounded-cache eviction in independent
  fixtures with three wording variants.
- [x] Add executable-syntax ArkTS markers and language-neutral query concepts
  without project aliases or inferred missing repairs.
- [x] Require UI context for ambiguous visual-cover terms so data overwrite
  queries do not activate overlay retrieval.
- [x] Expand the development gate to 50 scenarios and 150 variants and retain
  a 150/150 pass before external observation.
- [x] Review and seal four ccplayer fixes, execute the pack exactly once, and
  retain the immutable failed observation.

The thirteenth-project observation passes 1/4. Surface callback/render
coordination passes. Repeated session cleanup finds its owner only as a late
expansion without an excerpt, while source-replacement state and prepared-state
command eligibility owners are absent. The pack is consumed and cannot be
rerun. Further repair requires independent fixtures and a new sealed project;
no ccplayer name, path, task phrase, threshold, or Oracle may enter tuning.
