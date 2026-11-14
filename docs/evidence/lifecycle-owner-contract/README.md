# Lifecycle owner contract audit on current production

Baseline `6188afe` (production code unchanged after `63970fc`). Development audit,
not a serving change. No original-case or full gate was rerun; repaired-original
count remains 20. The old non-erasure candidate remains rejected.

## Current public result, not inferred from historical outputs

The four unchanged frozen lifecycle-0..3 fixtures/queries from
`docs/eval/semantic-focus-contract/protocol.json` were materialized once and learned
normally with the public CLI. Required/forbidden path checks were retained.

|case|compact paths|result|tokens / 1500|
|---|---|---|---|
|English composite|BufferSession|pass|1163|
|Chinese composite|PendingQueue|FAIL, BufferSession missing|1082|
|explicit append|PendingQueue|pass|967|
|explicit both|BufferSession, PendingQueue, WriteQueue|recall check pass, not precision claim|1421|

A runner omission of the promised trace was corrected transparently in the protocol
before one additional unchanged Chinese raw query. The observer returns original
results; traced/clean raw code anchors are equal. This is five raw executions and
four compact executions, four acceptance cases, not a fifth test or a tuned trial.

## Exact current first loss and source contracts

At focus input, PendingQueue.append has semantic coverage 2 and score 12;
BufferSession.reload and commit each have coverage 1 and score 9. Structural
BufferSession file evidence is present at score 6. Focus returns only append.
`strongest_semantic_behavior_candidates` explicitly selects maximum per-item
coverage when it is >= 2, at most two paths. No same-owner aggregate certificate is
constructed or consumed there. Changing that is not repair of a dropped certificate.

Read-only SQLite inspection provides a more precise bound than simply saying
"the typed graph is present":

- All 16 indexed symbols have source identities; BufferSession's class plus three
  methods share the exact same file digest. Methods have owner_name BufferSession.
- The single symbol-to-symbol semantic edge is **onMount -> reload**, `calls`,
  line 4, static 0.95 confidence. There is no call connecting commit to that chain.
- `onMount` has role lifecycle, with method hints lifecyclehook/lifecycleactivation/
  lifecycleboundary, but **not lifecyclesync**. It is absent from the Chinese focus
  input. A hook-name role is not itself the query's lifecyclesync marker.
- reload has state_write plus **source_operation_unresolved:persistenceread**;
  commit has persistence_write. The untyped external cache.load/save receiver is
  not an identified storage instance or proof that both operations share one key.
- There are **no reads_state/writes_state edges** for these plain private fields.
  Current semantic_ecma's typed state-access extraction is bounded to decorated
  state names. The method text hints are broader. Absence of those edges is not
  absence of state operations and does not justify excluding this real owner.
- Same-file SplitRoles methods retain three different owner_name values. File
  aggregation would wrongly combine unrelated owners; copying file hints to each
  method is still disallowed.

The old broad statement that every correct method simply covers a subset should
not be strengthened to "all three requested markers can already be unioned from
known methods": in this independent fixture lifecyclesync is not attached to its
hook. Merely grouping callable_roles or matching owner strings cannot recover a
pre-existing three-marker certificate. It would create a new one.

## Decision and next evidence requirement

Existing fields can support a **non-exclusive source fact display**: list method
IDs/keys/ranges under the same file digest and owner_name, and expose the observed
static call with its evidence. No new schema is needed merely to display those
already-stored facts. The owner_name is not a global unique owner ID, the method
roles are not a composite permission, and such a display cannot activate ranking,
exclude partial competitors or assert runtime restore/commit causality.

No runtime/test patch. The exact public red persists, but the requested repair
would introduce owner aggregation plus interpretation of a lifecycle call chain,
not fix an existing typed permission being discarded. The static call proves
invocation syntax, not framework lifecycle invocation, storage provenance, restore
success or commit execution ordering. The case does not require proving all those
runtime properties, but any proposed source contract must state these limitations.

A bounded design would need (1) source-bound unique owner identities rather than
file unions; (2) explicit operation facts per method and conservative unresolved
states; (3) narrowly stated static hook/call evidence, no inferred runtime dataflow;
(4) a separately validated request permission to combine those roles; and (5) a
second independent defect class demonstrating the same missing aggregation
contract before architecture implementation. No such second class was established
in this audit. Visual alternatives, Builder decorators and Listener callbacks are
not interchangeable evidence for it. Stop this candidate path rather than expand
scores, top-N, markers or query synonyms.

Evidence: `public.json`, `summary.json`, `code_symbols.json`, `memory_edges.json`,
`selection-trace.jsonl`; fixture hashes in `freeze.json`. All outputs are synthetic
Development with temporary workspace paths, not external/holdout evidence. Source
and queries were not modified after results. No GitHub publication attempted.
