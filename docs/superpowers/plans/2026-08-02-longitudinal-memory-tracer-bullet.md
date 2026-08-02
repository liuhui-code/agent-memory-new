# Longitudinal Memory Tracer Bullet Plan

## Objective

Exercise one real four-Skill loop across two ordered ArkTS tasks:

```text
learn -> query -> solve/review -> reflect -> source advances -> refresh -> query/reuse
```

The first run is a development observation. It does not create a holdout, claim
generalization, or authorize serving changes. Its purpose is to find the first point
where the current product loop fails in normal use.

## Source And Evidence

- Repository: `wbbb0/wPlayer`
- License: GPL-3.0
- Development clone: `/private/tmp/agent-memory-wplayer-development`
- Repository use before this plan: none found in `docs`, `tests`, or `gitlog.md`
- Task A commit: `bf50aeec21f3de19347a3169a3ca6b4968a48fb0`
- Task A parent: `ef8b2abb8e607c8cf2abfb0bfd5d6cc070f060b6`
- Task A subject: `perf: keep import and file check responsive`
- Task B commit: `f6282246bc9d26d7f35ede5bd566a2bad0be93d7`
- Task B parent: `0be04a1b729170a87a8b7b3cd832862d3337abb0`
- Task B subject: `优化音乐文件检查流水线与中断`

Both tasks modify the library importer domain. The reviewed diffs overlap
`MediaImporter.ets`, `MediaPickerService.ets`, `ImportConcurrencyPolicy.ets`, and
risk-regression checks. Task A introduces bounded batches, UI yields, and throttled
progress. Task B adds cancellation-aware permission work and a bounded inspection /
artwork pipeline. These facts come from commits and source diffs; no runtime symptom,
log, or causal statement is invented.

## Method Basis

- LongMemEval separates long-term memory into extraction, multi-session reasoning,
  temporal reasoning, knowledge updates, and abstention:
  <https://arxiv.org/abs/2410.10813>.
- LongMemEval-V2 evaluates whether accumulated trajectories provide compact,
  environment-specific workflow and failure-mode evidence to a later Agent:
  <https://arxiv.org/abs/2605.12493>.
- The repository evaluation policy requires editable development reproduction before a
  serving change and forbids consumed holdout tuning. This run remains development.

The tracer follows test-then-learn ordering: Task A is queried before its reflection is
written; Task B is queried only after the source advances and Scope refresh completes.

## Boundaries

- Use the existing four Skills and `tools/agent_memory.py` only.
- Use an isolated memory home under `/private/tmp`.
- Persist no raw runtime logs or private reasoning.
- Store only a compact Agent-authored reflection grounded in Task A source and diff.
- Do not modify Runtime, ranking, thresholds, schema, or evaluation cases during the
  observation.
- Do not call the development source a holdout and do not seal it.
- Treat source at Task B parent as authoritative over Task A memory.

## Execution

1. Checkout Task A parent and learn only `entry/src/main/ets/library`.
2. Query Task A through compact Context and inspect returned parse/freshness/anchor
   evidence. Review the current source and Task A diff.
3. Write one `procedure_experience` with trigger, repair action, verification method,
   applicability, negative preconditions, and source cases. Run reflection review.
4. Checkout Task B parent and run changed-only Scope maintenance. Confirm only learned
   Scope changes consume refresh work and the Task A experience remains active.
5. Query Task B through compact Context. Record whether Task A is retrieved in the main,
   guard, or omitted lane, and whether current-source anchors cover the importer,
   permission, store, and policy boundaries actually changed by Task B.
6. Compare the retrieved guidance with the frozen Task B diff. Record `helpful`,
   `ignored`, or `misleading` only from that comparison.
7. Run `maintain-health`, `reflect-review`, and focused SQLite inspection. Record the
   first broken stage and stop. Add implementation only after an independent second
   development defect proves the same missing contract.

## Observation Contract

Record these facts for each stage:

- command and source revision;
- learned Scope and parse counts;
- compact Context Token estimate;
- primary code/log anchors and freshness;
- returned reflection id, lane, trust, applicability, and counter-evidence;
- refresh candidate and refreshed file counts;
- whether current source contradicts prior memory;
- whether the prior experience materially narrows Task B inspection;
- first broken stage: activation, learn, query, capture, refresh, retrieval, use,
  interference, or none.

## Stop And Acceptance

The tracer passes only when:

- Task A is learned and queried from its parent revision;
- its reflection is accepted as a structured candidate without placeholders;
- Task B refresh preserves the reflection and refreshes the changed learned Scope;
- Task B Context returns current source evidence and handles Task A experience without
  authority inversion;
- an evidence-backed usage outcome is recorded;
- no raw logs, diagnosis, holdout claim, fifth Skill, or source mutation is persisted.

Failure is an acceptable result. Stop at the first evidenced break instead of adding a
feature speculatively.

## Execution Outcome

- Task A learned 36 ArkTS files and produced a grounded `procedure_experience` from
  commit `bf50aeec`. Its first review correctly remained `never_applied`.
- The first changed-only refresh advanced the Scope from `ef8b2ab` to `0be04a1`,
  refreshed 20 in-scope files, reported four changed boundary dependencies, and did not
  expand those dependencies into the learned Scope.
- A procedure-focused Task B query recalled reflection 1. Comparison with commit
  `f628224` showed it was helpful for batch, yield, and progress constraints but did not
  replace current-source inspection for cancellation propagation and bounded queues.
  A verified `helpful` usage event was recorded.
- The second refresh advanced only four changed Scope files to `f628224`; freshness was
  `current` at generation 3. Reflection 2 records only the additional cancellation and
  backpressure evidence. Governance requires confirmation before promotion.
- An unrelated playback-rendering procedure query returned no experience, so this run
  found no stable experience-interference failure.

The first stable failure was intent selection. In the real wPlayer output, a Chinese
action-style request selected `code_location`; an English `how should` paraphrase also
selected the wrong lane. An independent cache-refresh development fixture reproduced a
second collision: the domain operation `refresh` selected `memory_maintenance` even for
a procedure request. The common missing contract was a caller-declared evidence intent.

The implemented repair adds optional typed intent to the existing Context facade while
preserving lexical inference for compatibility. It changes only lane gating and exposes
`memory_intent_source` for audit. Pure cross-language candidate recall remains an
evidence gap: explicit intent cannot retrieve an English-only reflection from unrelated
Chinese tokens. The Query Skill therefore delegates language normalization to the local
Agent and accepts Agent-extracted source terms without introducing Runtime translation,
embeddings, or a fifth Skill.

## Verification

- Typed-intent development fixture: 2/2.
- Focused intent, experience, retrieval, Context, log-path, and repository-design
  regression tests: 73/73.
- Restricted complete suite: 810/813 passed on the first run. Two errors are the known
  loopback bind restriction. The only real failure was the Query Skill 120-line gate;
  after moving detail to progressive disclosure, its complete module passes 7/7.
- CI scale: pass at 100,000 searchable entities and 300,000 edges; all latency,
  query-plan, and incremental-maintenance gates pass.
- Python compilation with a sandbox-local bytecode cache, all 193 JSON files, diff
  hygiene, exactly four Skills, and the 500-line code gate pass.
