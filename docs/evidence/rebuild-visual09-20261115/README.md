# Reimplementation of visual background request 09 (Development only)

This is a fresh implementation on published production base fced64c4 via local
066cc1a, not recovery of the lost 55 commits or their prior tests. The protocol
was committed as 83ad9cc before this work's public baseline and production edits.
No original queries, fixture source, oracle, scoring threshold or budget changed.
No full suite or sealed/holdout evaluation was run.

## Actual observations and result

- The unchanged independent AmountSurface/GestureLayer background request failed
  precision before this change: both paths were returned. This differs from the
  much older recorded result that returned only GestureLayer. Exact target,
  exact competitor and explicit-both controls already passed.
- First source-witness candidate made those four independent checks pass, but
  original09 stayed **1/3**. The failed attempt is retained in `candidate-*`.
- A current read-only pool inspection confirmed InventoryOverlayPanel.build was
  retrieved but removed by semantic focus before the bounded trial. This is not
  missing indexing, absence of source, or license to change global focus rules.
- The final request-bound candidate-pool transport passes all four independent
  checks, and original09 **1/3 -> 2/3**: original English stays pass; English
  paraphrase stays fail; Chinese changes fail -> pass. Chinese compact is 790
  estimated tokens, with the full unchanged build span 5..16. The other two
  variants retain their previous paths and token estimates. This is one newly
  re-established original variant, not three repairs or an aggregate score.
- Four additional public controls pass: renamed owner/observation, two positive
  background owners retained, unsupported helper source not promoted, and
  negative request not promoted. These were frozen before their public runs.

## Mechanism and boundaries

The already-existing render request/trial/same-read snapshot channel now also
recognizes a closed Chinese request for ArkTS background styling. Its optional
observation has a bounded noun/遮挡-or-覆盖/noun form; negative, compound, identity,
extra-request and unsupported syntax remain on the unchanged baseline.
Observation nouns never supply owner identity. This is not a general Chinese
semantic parser or a new broad layout alias.

The background recall projection adds only the named `backgroundcolor` capability
in the explicit opt-in trial. A private, query/snapshot-bound trial transports
already retrieved matching method evidence before semantic focus; at most 12
paths are inspected, no global filesystem scan. Indexed words only identify the
inspection pool, never grant source authority. The original context remains the
public/copy/serialization fallback.

A bounded parser recognizes a single unshadowed component with literal fields,
a direct nested built-in UI build and direct backgroundColor modifier. Current
UTF-8 bytes, digest, generation, declared owner, method identity and exact range
must agree with the index and original retrieved symbol. Constructors and Color
cannot be shadowed. Comments/strings are not calls. Imports, callbacks, helper
calls, complex expressions and other unsupported syntax produce **unknown**.
Unknown owners are not certified absent: this projection presents positive source
witnesses only and never claims the complete/exclusive owner set, overlap cause,
color value, execution path, or runtime behavior. Multiple supported positive
owners are retained, or the whole candidate falls back if complete snapshots do
not fit the unchanged 1500-token envelope.

Existing identity/graph/path/log protections remain. Snapshot display uses the
same bytes validated during selection, not a later reread. Trial and final view
mutation/copy lose projection authority. Lifecycle and cleanup behavior stay on
their existing contracts. No non-erasure veto, ranking weight/threshold, fixture
word tuning, oracle adjustment or full-gate claim is introduced.

## Checks and retained failures

- 43 background/render source, recall, selection and transport tests pass.
- 39 related lifecycle, UI-pair and source-excerpt tests pass.
- Independent baseline/final: 3/4 -> 4/4. Extra public controls: 4/4.
- Original Development09: 1/3 -> 2/3. The English paraphrase remains red.
- Initial related-test command named a nonexistent module, yielding one import
  error; its log is retained. Correcting the command, not the tests, gives 39/39.
- Repository fingerprint check fails on 14 pre-existing evidence scripts.
  `fingerprint-baseline.json` independently checks each against 066cc1a; all
  existed there and already omitted the fingerprint. No new omission. This
  inherited failure is not waived and this work does not claim a green full gate.
- Changed production files remain within 500 lines; `git diff --check` passes.

The evidence contains synthetic fixture outputs, temporary workspace paths and
assessment metadata. Local commits and bundle are for parent review/integration;
this worker performs no remote write and does not modify main.
