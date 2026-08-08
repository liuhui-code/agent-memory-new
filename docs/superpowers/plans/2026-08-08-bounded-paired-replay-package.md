# Bounded Paired Replay Package

## Status

In progress. Completion requires every controlled development regression below
and the repository verification gates.
This is an evaluation-control-plane change. It does not change Context retrieval,
ranking, graph construction, Runtime diagnosis, or the four-Skill interface.

## Problem And Evidence

The prospective cohort records a task digest, a clean Git status snapshot, and a
Memory manifest. The former paired benchmark binding accepted a result when its
case id matched and its v3 measurement contract passed. It did not prove that the
Agent pair used the enrolled task, the enrolled source revision, or task-start
Memory. `prepare_isolated_memory` rebuilt an empty isolated archive and indexed
the materialized source, so it could not replay the original Memory state.

These are three independent, controlled defect classes:

1. A result for a different task can reuse the linked case id.
2. A result can use a different clean source revision.
3. A result can use rebuilt or different Memory while preserving a manifest-like
   summary.

They all identify the same missing contract: immutable input identity is not a
first-class part of a paired measurement. This meets the repository policy's
requirement for an architecture change without relying on an external score.

## Two Explicit Contracts

### Cohort Enrollment Attestation

Every natural task keeps the existing privacy-minimized record: raw task digest,
source state summary, Memory manifest, evidence references, usage aggregate, and
hash-chain entry. It proves only registration order and point-in-time metadata.
It creates no source archive, has no causal claim, and may include dirty or
unversioned work as observational data.

### Paired Replay Package

Only an automatically selected, clean candidate from a frozen protocol receives a
package. The package is a bounded local evaluation artifact, not project memory
and not an Agent wrapper. It binds these inputs:

| Input | Evidence |
|---|---|
| Task | opaque task digest, cohort id, sequence, and task id |
| Source | repository identity digest, Git revision, Git tree digest, clean state |
| Memory | task-start SQLite backup digest, byte size, manifest digest |
| Skill | digest of the installed `agent-memory-query` Skill contract |
| Runner | executable content digest |
| Environment | bounded Python/platform execution digest |
| Protocol | frozen protocol digest, treatment mode, case pack digest and schedule |

The durable cohort row exposes only metadata and digests. The local package
manifest holds the source root and snapshot path required for replay; it stores
no raw task, query, temporary log, source body, or model reasoning. The source
SQLite backup is immutable and byte-capped. Each replay gets a temporary writable
copy so normal query accounting cannot modify the immutable package.

## Candidate Selection And Lifecycle

The optional `paired_replay` protocol field is either disabled or declares a
deterministic `first_eligible` rule, a fixed candidate count, snapshot byte cap,
and retention policy. The first eligible arrivals consume candidate positions
even when they are dirty or exceed the cap. This prevents later cherry-picking.
The default is disabled for backwards-compatible observational cohorts.

At enrollment, the control plane captures the source identity and, for an eligible
candidate with a clean source, takes a SQLite-consistent backup before inserting
the cohort row. It records `ready`, `source_ineligible`, or `snapshot_exceeded`.
The original package snapshot is chmod read-only. The recorded retention policy
sets the manual retention window; automatic deletion is deliberately excluded so
a failed or incomplete replay remains auditable and cannot silently lose evidence.

## Replay And Binding

`eval-agent-benchmark --paired-replay-package` is the narrow evaluation adapter.
It requires an external runner, one validated case with the same id and explicit
task-digest binding, the exact enrolled Git revision, no fixture or mutation, and
the frozen snapshot. It cannot use recorded responses because those lack trusted
execution identity.

The Runtime creates the attestation after materializing source and preparing
Memory; it does not trust a Runner-provided assertion. The final result contains
only digests and stable metadata. `eval-cohort-complete` rejects results that do
not exactly match the selected package. Legacy v3 results remain readable as
historical calibration output but cannot establish a paired cohort conclusion.

## Acceptance Checks

- [x] Protocol validates deterministic bounded replay selection.
- [x] Controlled task, source, and Memory misbinding attempts fail closed.
- [x] A clean enrolled task creates a read-only, byte-bounded snapshot package.
- [x] A paired benchmark verifies task/source/Memory/Skill/Runner/environment
  identities before producing an attachable result.
- [x] Cohort reports count only package-bound replay results as paired evidence.
- [x] Existing natural cohorts stay observational and privacy-minimized.
- [x] Focused tests, complete test suite, scale gate, and 500-line gate pass.

## External Practice Basis

- Microsoft ExP, [Patterns of Trustworthy Experimentation](https://www.microsoft.com/en-us/research/?p=680556): preregister hypotheses, metrics, and stopping rules before exposure.
- Microsoft ExP, [During-Experiment Stage](https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/patterns-of-trustworthy-experimentation-during-experiment-stage/): preserve treatment integrity and do not select based on interim outcomes.
- [SWE-rebench V2](https://arxiv.org/abs/2602.23866): reliable software evaluation requires reproducible environments and instance-level contamination control.
- [SWE-Bench-CL](https://arxiv.org/abs/2507.00014): chronological tasks must remain distinct from unordered historical samples.
- OpenTelemetry, [Handling sensitive data](https://opentelemetry.io/docs/security/handling-sensitive-data/): collect only bounded data needed for the stated observation purpose.
