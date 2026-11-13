# Rejected global ArkTS language-only translation (Development)

Base5fffbd7 runtime equals9d2dba8; frozen original protocol/red commit d6b4a4a.
No accepted production change. tools/tests are restored to base exactly.

## Proven problem, incomplete remedy

Current text.query_tokens maps ArkTS/ets together with Harmony/HarmonyOS/鸿蒙 to
harmonyos/arkts/ets/entry/ability/stage. A frozen independent GlyphList UI request
selects EntryAbility when ArkTS is added, while the otherwise identical plain
request selects GlyphList correctly. This is a real public retrieval pollution
example, not merely a token-unit discrepancy.

Candidate separated only ArkTS/ets into arkts/ets aliases, retaining broad platform
expansion for 鸿蒙/harmony/harmonyos and leaving intent/ranking/scope untouched.
UI language query became correct. Existing explicit Ability/Stage, platform named,
qualified owner and ArkTS lifecycle controls remained correct. Algorithm domain
was NOT fixed: ByteMixer.ts expected queries with ArkTS/ets still fail, now with
EntryAbility+GlyphList instead of EntryAbility. Their changed output must not be
called unchanged. The plain checksum query is empty before/after, and the plain
byte-mixing query succeeds before/after. The TS-vs-ArkTS source distinction remains
an explicit fixture limitation, not a reason to change its expected result.

Original post-hoc checks: ArkTS UI remains0/3. The original variant gains the correct
InventoryList span but still retains extra owners, so it is NOT newly passed.
Abstract-scroll remains1/3. No new original failure-count improvement is claimed.

## Decisive additional positive controls

Reviewer requested genuinely platform-related application startup/initialization
queries that do not spell Ability or Stage, avoiding overlap with other unchanged
triggers. startup-protocol.json froze four English/Chinese queries and EntryAbility
with its stage.loadContent body as expected before baseline/candidate execution.

All four pass on the unchanged baseline runtime. Candidate:
- English ArkTS application startup: EntryAbility plus unrelated GlyphList.
- English ets application initialization: same extra owner.
- Chinese ArkTS application startup: wrong ByteMixer only.
- Chinese ets application initialization: wrong ByteMixer only.

These are NEW REGRESSIONS. They are not expectedFailure tests and expectations were
not changed. A generic language-only split therefore cannot be accepted, even though
one independent UI defect improves. Do not add a startup-word exception to conceal
the cross-intent compatibility problem. A later remedy needs evidence-conditioned
interpretation of language references versus implicit platform owner requests, with
both families preserved and genuine ambiguous requests left open.

## Evidence and checks

- before.json is initial exploratory nine-query run. Before any production edit,
  protocol gained byte-mixing and platform/lifecycle controls; frozen-before.json
  records the final15 original protocol queries. No initial failing query was deleted.
- after.json matches those15 unchanged queries and expected owners.
- startup-protocol / startup-before / startup-after are supplementary frozen controls,
  compared unchanged against the same source content and old/new runtime.
- Original UI and scroll have separate before/after selected reports, no full suite.
- focused.txt ran33 tests:30 pass,3 pre-existing/recorded expected failures before
  the decisive additional guard. It is NOT final acceptance or all-green evidence.
- rejected-language-only.patch and candidate-tests.py.txt preserve the rejected
  candidate; no candidate test remains installed and no new regression was weakened.
- probe.py uses the formal CLI through the test harness; startup-probe.py supports
  RUNTIME_REPO to select the detached unchanged baseline runtime. No source oracle
  or intent contract was altered, and no remote publication/full gate/holdout ran.

Separate observation: substring ets can trigger in packets/assets identifiers.
Another worker is investigating that distinct token-boundary defect. No matching
boundary was changed here; do not attribute its possible result to this rejected
language-group experiment.
