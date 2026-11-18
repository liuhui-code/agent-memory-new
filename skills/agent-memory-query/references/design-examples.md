# Worked Design Examples

Read only the relevant example. Synthetic examples illustrate judgment; they
are not observations of an Agent, benchmarks, or evidence of efficacy. The
historical case below has its own bounded source and limits.

## Local Change: Do Not Create A Design Problem

Synthetic input: change the fixed navigation label "Profile" to "Account".
Current source has one label constant and one consumer; no behavior, schema,
localization or public API changes are requested.

Reasonable decision: edit the label and inspect the affected rendering or
existing check. A provider registry, a new translation framework, three
candidates or a full ADR do not respond to this input. Follow existing routing;
an explicit request to query Memory still takes precedence.

Countercondition: if the request actually requires per-user locale selection
or a public key consumed elsewhere, inspect that contract before deciding.
The lesson is to scale design work to the task, not "never abstract labels".

## Historical Case: ArkLog Stream Isolation

Classification: historical development evidence, summarized from repository
document `docs/arklog-m1-design-experiment.zh-CN.md` and its recorded native
experiments. Source: ArkLog commit
`9aa4c503c271ab22375ec5e40e645f536b441c11`. Full evidence is repository-only;
an installed Skill must not assume those files are bundled or currently valid.

Drivers: reject obsolete stream batches, preserve valid manual-Stop tail
batches, and finish old cleanup before replacement. Current production TUI
coordinates those transitions through the existing Controller and Runtime.

Decision: keep that state owner and full stream-ID gate. Native probes
distinguished same-device generations, current valid batches, completion
identity, and replacement ordering. Deliberately wrong controls exposed the
importance of both identity and cleanup ordering; an older A-to-B test alone
did not distinguish the device-only control.

Reference fit: explicit ownership and lifetime analysis explain why existing
serialization is sufficient for the checked production path. Adding a new
SessionManager has no demonstrated benefit in this case.

Limits: this is not proof of every public-call ordering, hardware behavior,
cross-platform correctness, or universal superiority of one Controller.
Removing cleanup ordering invalidates the rationale. The recorded Memory
Rust-source result was empty; actual source inspection by the Agent and native
tools supplied this case's evidence. Do not describe it as a measured Memory
benefit or an unseen evaluation task.

Revisit if a new caller bypasses the coordinated start path or multiple
independent owners must commit concurrently. First establish the new behavior
and a controlled counterexample; do not transfer this case as "always use a
single Controller".

## Historical Advice Conflicts With A Current Requirement

Synthetic input: decide whether a balance reader should cache results.
The reviewed current requirement says the next read after a committed update
must see that update. A historical Memory record recommends a time-based cache
for an unrelated catalog. No current performance problem has been measured.

Input guidance should surface all writers, consistency scope and workload as
consequential unknowns. The old case matches repeated reads but does not
establish the same freshness requirements or invalidation ownership.

| Option | Consequence under the stated scenario |
|---|---|
| Keep direct reads; measure before adding a cache | Preserves stated semantics; performance improvement remains unproven |
| Add a time-to-live cache without invalidation | A committed update followed by a cached read can return the old value; violates the requirement |
| Validate or invalidate entries across all writers | Could preserve semantics, but ownership and cost must first be established |

Decision for this decision-only task: do not introduce the proposed time-based
cache. Retain direct reads while obtaining the missing workload evidence.
This does not complete a separately requested performance implementation.
If latency already fails a hard requirement, keeping direct reads alone is
insufficient: leave the design unresolved until a viable mechanism is found.

Useful feedback would describe the mismatch in freshness and writer ownership,
not a general "caching is bad" rule. Revisit when measured pressure and a
complete invalidation/validation path justify the cost. Record misleading or
superseded Memory reuse through the existing feedback path, without claiming
that one such example establishes Memory's overall value.
