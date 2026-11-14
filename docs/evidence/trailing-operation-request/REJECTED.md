# Trailing-operation producer candidate: rejected for production integration

Candidate source commit: `d06114c` (after `b98052f`, `6a8f91d`, `14e1eda`). Baseline runtime
is `f3e217b`; independent design/before/corrected-budget freeze ends at `873f698`.
Development only. No evaluator/query/oracle changes, no full run, no consumer change,
no public write. The candidate stays isolated; only this diagnostic evidence is
eligible for integration. Cumulative repaired original variants remains **20**.

## Decision and exact failing contract

The frozen `protocol.json` says for `quoted`:
`preserve before log/path and code-owner behavior; no new eligibility`.
For `negative_conflict`: the same text. These were not just source-scope checks.

- `字号显示错误，请定位 "fontSize" 的源码。`: code owner was `CaptureLogger.ets`,
  candidate yields `StatusCaption.ets`. Preservation **fails**.
- `字号显示错误，请定位 fontSize 的源码，不要返回 fontSize。`: same owner change;
  preservation **fails**.
- All eight fixed requests retain byte-equivalent compact `log_anchors` and
  `path_context`; the two failures are specifically code-owner behavior changes.

The simple runner emitted null for these policy controls, not pass. Explicit
`producer-fixed-control-verdicts.json` now evaluates the frozen preservation
conditions and reports false. This does not change the oracle or relax it.
Relative to the precommitted compatibility contract this is a regression, even
though a typography source can seem semantically reasonable for a quoted name.
No claim is made that the old logger was an ideal answer. The conflict boundary
cannot be dismissed as desirable improvement. A producer fact enters existing
retrieval/localization ranking independently of the paused consumer; retaining all
logs is insufficient to preserve the specified code-owner behavior.

The source request itself improves from only `CaptureLogger.ets` to only
`StatusCaption.ets`, satisfying its unchanged required/excluded paths. Qualified,
true event, explicit logger owner, and multiple-source required-path controls all
pass. Unknown retains empty code anchors. Thus five required-path checks pass,
one preservation check passes, two preservation checks fail. Do not call this an
8/8 acceptance or an accepted repair.

## Producer-only scope observations, with unresolved review counterexample

The candidate adds case-preserving `call:.fontSize` / `call:.fontColor` positive
static syntax observations to the existing operation mechanism, with unchanged
source key, line, method range and raw-byte digest. It does not establish receiver
type, runtime execution, causal effect, source-operation completeness, uniqueness
or absence. No schema/role version upgrade. The intended unsupported-syntax
boundary is no new fact, but the final multiline-computed counterexample below
shows that the candidate does not fully enforce it.
Unknown nested blocks are not implicitly outer-method bodies. Only known declared
methods and bounded known construction scopes are considered. Expression-bodied
arrows, unknown slash/template interpolation/unbalanced syntax remain unsupported.

New observations append after the complete old sequence, protecting existing
(source_key, kind, line, terms) keys and spare caps of 8 operations/line and 16
mechanisms/callable. Initial `capacity` / `total_capacity` frozen examples actually
had only 1 / 2 old facts due deduplication; their original text and observations
remain saved, not represented as full-cap checks. Separate preimplementation
`capacity-protocol.json` proved 8 distinct same-line keys, 16 independent-line keys,
and a real lowercase padding collision. Final candidate preserves all 8 / 16 / 1
respectively and adds none. The 15 frozen source examples retain old entities,
gaps and full original mechanism prefix; new facts preserve exact detail case.

Public CLI activation probe: old normal learn produces 7 symbol rows. Installing
candidate code without learn leaves all 7 public list rows exactly equal. Normal
merge learn on unchanged source bytes adds typed method facts, generation 1→2;
stable keys, range, signature, digest, callable roles and existing evidence remain.
SQLite row ids are reinserted, not preserved identities. In particular
`source_operation_checked:v2.1` is unchanged; it is not upgraded by this addition.
The first probe mistakenly supplied unsupported `init --json`, failed before
learning, and was corrected to the existing CLI; setup error is retained.

## Review corrections and focused evidence

The initial uncommitted implementation incorrectly treated any closing `)` / `}`
as a base. Reviewer actual probes found control/arrow/function/bare-block closing
false positives and uppercase nested functions misattributed to the outer method.
`b98052f` fixed completed-base qualification but still misattributed unrecognized
nested class getter/generator bodies. All observations are retained in
`review-tail-scope-observations.md`; they are not acceptance successes.
`6a8f91d` conservatively blocked unknown nested scopes but accidentally included
the enclosing class, causing 12 subtest failures; retained log records this.
`14e1eda` confines that block check to the declared method body. New tests preserve
real Text/Column positives while rejecting these unsupported cases. Final review
then found optional receiver prefixes still admitted; d06114c rejects optional,
computed and unsupported new-constructor bases, rather than expanding grammar.
The observed optional/new counterexamples remain in the review record.
Final independent review still finds unsupported multiline computed bases leaking:
`foo[bar]\n.render()\n.padding(8)` and
`obj['Render']\n.factory()\n.padding(8)` both emit a new outer-method fact.
The expression-prefix check resets at newline. This remains unresolved on the
isolated rejected candidate; **do not call its source-scope contract fully safe
or accepted**. The final review ran 16 focused tests successfully, but these
additional counterexamples are not covered by those tests. Further speculative
parser patching was stopped after this final review, as directed.

Final focused run: **40 tests pass** (9 new + 31 related). Separate fingerprint
check: 1 passes. Compile and diff whitespace checks pass. Runtime files remain
483 and 148 lines, under the existing 500-line limit. These runs are not a full
gate. Source controls and activation are separate probes, not added to 40.

Unchanged original04 Development group: **0/3 before and after**. Original remains
WorkspaceAbility only; English remains InventoryItem + InventoryList + Overlay;
Chinese remains DispatchProfileService + InventoryList + Overlay. Precision for
the latter two stays 1/3. Explicit InventoryRecord/InventoryItem exclusions in the
Chinese query already worked and are not modified. The new independent positive
request gain is not counted as an original failure repair.

## Next boundary

Do not add posthoc quoted/conflict query special cases to make this candidate
pass. Consumer remains paused: the independent before implicated callable
localization and independently recalled wiki logger evidence, not weak-only log
promotion. Future work needs a separately frozen supported evidence-admission or
retrieval contract with its own independent actual before and compatibility
controls, or another remaining failure class. The isolated producer experiments
can inform it but cannot authorize production behavior or a new architecture.
