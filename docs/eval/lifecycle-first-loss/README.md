# Lifecycle persistence: first-loss trace and a missing negative control

Base f9ecd08. Development only; no runtime, score, threshold, oracle or budget edit.
Only the original lifecycle-persistence group was rechecked: original passes;
English and Chinese fail (1/3). This is not a completed repair or a global blocker.

## Previously unknown first loss is now identified

The correct DraftSessionCoordinator is NOT absent from initial retrieval:
`first-loss-summary.json` retains the complete focus inputs for both failed queries.
The class, file and aboutToAppear/restoreDraft/saveDraft methods are present with
correct source intervals. In the English query restoreDraft scores 49.0, saveDraft
46.25, file 43.4; this is not simply a low initial retrieval score.

`focus_code_candidates` first applies strongest_semantic_behavior_candidates. The
query requests lifecyclesync + statewrite + persistencewrite. Each correct method
covers a subset, while ConversationDraftStore.queueIncrementalWrite covers two
within one method (state write + persistence write, no lifecycle sync). The current
selector accepts maximum coverage >=2, chooses that single method and drops the
correct multi-method owner from its focused output. Structural file evidence does
not grant individual methods a combined proof. Salient supplements later admit
other English competitors, not the missing coordinator.

Localizer is a separate view: English still retains DraftSessionCoordinator.saveDraft
as an alternative, while its primary is OrderCommitCoordinator.commitOrder and is
uncertain. Compact preserves the already-focused anchor list. Chinese similarly
ends with ConversationDraftStore. No symbol, source extraction or stored ownership
field was found silently lost. This is the partial-method focus versus composite
owner boundary, not a parser failure.

Trace wrappers record inputs/outputs and return the original results. Separate
clean/traced raw and compact code-anchor lists are identical for both failed
queries (four exact comparisons). Their callable ranges do not assert complete
excerpt contents; source-span overlap metrics must not be described as full text.

## Independent public negative control now reproduced

The earlier `docs/evidence/lifecycle-persistence` independent BufferSession family
was green against isolated writer, setter and split-owner classes. It did not test
a competitor covering two requested operations within one method.

This protocol extends that retained independent family, rather than inventing new
original-case keywords. PendingQueue.append assigns this.tail and calls cache.save
inside a queued callback, with no lifecycle restore. Existing queries and sources
are retained; the extra competitor and two controls were frozen before execution.

Actual public result:
- English composite request still returns BufferSession.
- Chinese composite request now returns PendingQueue: RED, with the desired owner
  absent. The prior no-PendingQueue control was green in the retained evidence.
- Explicit PendingQueue.append correctly returns that real implementation.
- Explicit BufferSession + PendingQueue retains both, plus WriteQueue. The frozen
  check is required-owner recall, NOT a claim of perfect precision.

No expectation was changed or converted to an expected-failure test. Independent
red is retained in independent.json, not used to claim a runtime improvement.

## Why no immediate threshold patch

The current heuristic explicitly permits partial two-marker focus. Raising its
threshold or assigning a whole file's markers to each method would be a behavior
contract/ranking change, not repair of a dropped producer proof. The latter can
mis-certify separate classes or unrelated methods. Neither was attempted.

The next implementable step needs a source-bound aggregate-owner representation:
indexed method identities sharing the SAME owner, explicit operation coverage per
method, lifecycle hook versus same-name calls, actual invocation links or clearly
stated non-dataflow limits, and unknown/missing adapters. Retain split classes,
same-name separate owners, genuine two-operation requests, explicit partial-method
requests and multiple real owners. Before changing architecture, establish a second
independent defect class for that same missing contract; a paraphrase is not one.
This trace and new negative control remove the old evidence gap, but do not justify
case-specific exclusions, invented causality or arbitrary weights.

22 relevant localization/profile/salience tests pass; fingerprint check passes.
No full evaluation, consumed holdout or original repair-count increase.
