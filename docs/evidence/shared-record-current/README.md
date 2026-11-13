# Shared-record aggregation: latest layer audit

Fixed baseline e760097 (callback lexical repair integrated). No serving changes.
Only this original scenario's three variants were evaluated: 1 pass, 2 failures,
unchanged from typed-reference follow-up. Chinese passes. This is not a full gate.

## First divergence and exact observations

Public raw/compact responses are in public.json. Trace return observations are
trace-0..7.json: init, learn producer, then raw/compact for each variant in order.
Tracing observes returns without mutating inputs or outputs.

All three queries initially focus the correct SharedRecordCollector file only.
Structural neighbor preservation does not add any source. Salient preservation
adds FolderCollectionLoader.loadFolder and CollectionPage for the original;
RecordPreview.build and SessionUsageCoordinator.recordSuccessfulUse for English.
These are independent lexical retrieval supplements, not graph or typed-ID errors.
Chinese receives no such supplements.

The producer extracts collect's correct method range (2..12); file-level summary
includes collectionfold. Callable behavior hints are only stateread/state/read,
while source-operation roles contain checked:v2.1, not an aggregation proof.
Original compact includes the complete target method. English localizer chooses
recordSuccessfulUse first and collect second. Compact preserves the target's
2..10 prefix with truncated=true, omitting return/end while also retaining both
other sources. This is an advertised budget truncation, not evidence the parsed
method boundary is wrong. Typed provenance is intact and not a new benefit here.

## Independent frozen mechanism controls

independent-protocol.json precedes the public run. ChunkAssembler directly
accumulates in a for-of loop; AfterIteration assigns only after that loop;
DeferredAssembly assigns inside a scheduled callback. All three receive the
existing file-level collectionfold marker. Exact named-method public controls
retain all three source identities/ranges. Exploratory generic iteration and
accumulator query selects AfterIteration; it has no collectionfold query marker
and is classified multiple. This is not presented as an acceptance red or proof
that the parser lost the real source.

The file marker's implementation explicitly checks a local declaration before
for-of plus a later scalar assignment. Existing tests cover a matching loop and
simple consumer, not lexical-scope/value-flow certification. It is a retrieval
hint, not a promised direct-iteration/source-operation certificate. Its matches
on these controls therefore establish a limit on using it as proof, NOT an
implemented data-dependency contract violation. No producer tightening is made.

## Safe boundary and next prerequisite

Both failing original variants request collectionfold and are classified multiple
(original-intent.json). The existing v2.1 consumer supports only runtimecapability
and persistenceread, with multi-target veto. Merely copying collectionfold to
method_evidence, increasing its weight, removing lexical supplements, or reusing
the withdrawn terminal-single rule cannot establish safe exclusion authority.

A future proof contract would need exact same-method loop bounds, direct writes
inside the loop, accumulator identity/use and nested deferred/after-loop unknown
controls, PLUS a request/consumer contract preserving true multi-owner targets.
The existing direct, after-loop and deferred controls can guard such a proposal.
This audit found no independently reproduced violation of an existing source
range or callback binding contract. It does not claim the remaining failure is
permanently unfixable; it locates the additional proof/consumer work required.
