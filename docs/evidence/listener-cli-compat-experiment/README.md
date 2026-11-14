# Disposable typed listener model / real CLI compatibility experiment

Base d4a4906. Only docs/evidence changes are committed. A temporary copy of tools
was modified and executed via its actual tools/agent_memory.py; normal SQLite
learning/indexing/listing, not fabricated output or direct SQL injection. The
experimental runtime is not a production patch or approved schema. No query
selector, ranking logic, oracle or fixed source changes.

## Chronology and exact results

Freeze9b77d1d protocol;6286c6d overlay/runner;eb5389e model checks. Attempt1 ran old
learn/list plus five before queries and code-only list, then failed at merge due
to copied module absolute imports (`tools` not importable in CLI package context).
2c38869 preserves its output and changes only copied module imports to relative.
Attempt2 repeats the same inputs in new isolated memory. Do not call this one run.

- Actual Relay index: old and code-only have zero new witnesses. Ordinary merge
  produces two witnesses on Relay.connect. Eleven stable source identity fields
  remain exactly unchanged (listed in summary.json). Adapter version is explicitly
  experimental; SQLite numeric IDs may rebuild and are not stable identity.
-20 fixed controls through actual init/learn/list: **19 pass, Native fails**. The
  Native expected two facts are missing. This is not evidence of no binding.
-11 specifically enumerated model checks pass: new roundtrip, legacy-without-new-
  field import as unknown, explicit old-reader schema rejection, seven corruption
  cases, and atomic byte-cap omission. This is NOT all protocol coverage or a safe
  deserializer certification. Missing checks/known risks are detailed below.
- Five fixed queries retain original outcome: generic binding red, four controls
  green. Actual code bodies/ranges and primary identity match. Four outputs have
  changed record_ids from merge rebuild; explicit Relay.connect budget increases
  892→893 due to larger numeric IDs. Other budgets987/986/969/987 unchanged, all
  below1500. No original failure improvement; no fresh original-group evaluation.

## Concrete failed integration boundary

The offline tuple preserves `listener.onFailure` and `listener.onReady`. Existing
`semantic_ecma_mechanisms.operation_mechanisms` passes chain strings through
`text.unique_list`, which lowercases them. Native indexed operation detail is
`call:listener.onfailure` / `call:listener.onready`. The experimental graft requires
exact source_key/line/detail and therefore refuses the mismatched case; Relay's
already-lowercase names graft successfully. Neither source nor join was changed
after this result. Case-insensitive matching would conflate valid different
identifiers and is not an authorized fix. A future design needs an explicit exact
source identity/position association, not descriptive detail as an identity key.

## Decoder and payload limitations found by review

The prototype only validates some fields. The eleven checks must not be generalized:

- New reader rewrites legacy schema v1 to experimental version; a v1 payload that
  already includes the new field is not explicitly rejected/cleared. The passing
  legacy test removed the field and does not cover this spoofed version case.
- Formal index/name/type are not all compared against entity.signature at decode.
  A different valid index or declared type can pass shape validation. Production
  source-time validate_witness is not a substitute for the deserialization boundary.
- argument_call receiver/member and coordinate_unit are not strictly validated;
  numeric ranges are nested and bounded but not independently attached to outer
  source offsets on decode. No arbitrary encoding/newline proof was tested.
- The cap check proves records are retained whole or omitted, not information-
  preserving compatibility. Enriching a legacy record with a large witness can
  consume4096 bytes, causing that record AND subsequent legacy mechanisms to be
  dropped by the current break policy. Actual small fixed inputs preserve bodies,
  but no general retrieval-invariance claim follows. Do not increase cap or silently
  discard existing mechanisms to rescue this experiment.

These are code-review identified reachable risks, not newly executed passing or
failing controls. They have not been patched to improve the reported result. The
protocol/model is **not ready for formal integration**. In particular old version
handling, lossless identity joins, strict decoding and preservation of old evidence
under payload budgets require a new explicit design/frozen test stage.

## Policy interpretation and scope

Initial PLAN used an overly categorical architecture-gate statement. Subsequent
review ff153ea distinguishes a finite optional local adapter/model extension from
a general scope/def-use framework or new exclusive serving authority. A protocol
change is real, but is not automatically a broad architectural change requiring
two classes. The existing weak direct-invocation case still does not establish a
second strong-contract bug. This experiment neither claims that gate satisfied
nor uses an overlay to bypass it: only experiment scripts/results are committed.
Any future production proposal must be reviewed on its actual bounded scope and
compatibility, with no generalized dataflow or exclusive ownership implied.

The fact is captured_parameter_member_invocation_in_call_argument, not runtime
registration/execution or positional value forwarding. Request-side selectors
remain unapproved; existing identifier token behavior is not patched. The unchanged
public red and failed Native persistence stay visible rather than being converted
to green by modifying queries, source, joins or scoring.
