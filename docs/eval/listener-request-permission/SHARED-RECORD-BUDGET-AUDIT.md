# Shared-record English: retained budget and recovery-contract audit

Read-only audit on 2026-11-14. No public query, candidate, or runtime execution.
Historical output remains historical: `docs/evidence/shared-record-current/public.json`,
`context-shared-record-aggregation-owner::en-paraphrase`, baseline e760097.
Current integration inspected at acf8c45. No current original-case pass claim.

## Actual saved fields

- Compact budget: 1421 / 1500, truncated=true; source freshness current, generation1.
- callable_evidence.primary is SessionUsageCoordinator.recordSuccessfulUse, range9–13.
  Its existing excerpt3–14 is complete, truncated=false.
- collect is an alternative with method range2–12, not the callable primary.
- SharedRecordCollector anchor: record_ids=[120], record_type=code_file,
  symbol=SharedRecordCollector, source_ranges=[class1–13], role=primary.
  Its excerpt instead identifies collect2–10, callable_mechanism_window,
  truncated=true. Role=primary does not mean callable_evidence.primary.
- RecordPreview and SessionUsageCoordinator are also retained anchors.
- Raw wiki row120 is kind=file, class1–13. Its digest is
  f3b1a6dad256dd3b15547fa2b0450152d828562fe3cfbf5464fd3820ff0de92b.

The retained fixture `docs/eval/fixtures/system-capability/src/sharing/SharedRecordCollector.ets`
still matches that SHA256 exactly. Lines11–12 are `return output` and method closing
brace. Existing excerpt is an exact prefix of source2–12.

## Arithmetic, not a recovery run

A deep-copy-only accounting calculation appended those two lines, updated excerpt
end/truncated and excerpt_chars, and recalculated the existing JSON-length/4 token
estimator including its budget field. It removed no other content or diagnostics.
Result: +22 source characters, total703 (was681), estimated1428 tokens. Thus this
saved payload has enough aggregate space for that tail. This does not demonstrate
that the current serving formatter produces the same payload, nor authorize a new
source-window choice. No recover function or public CLI was run.

## Why the current helper does not apply

`tools/agent_memory_runtime/context_source_recovery.py::recover_partial_primary`
(SHA256 27ba6b384bc9df40127e58371dc91898cae4627096d210f0a83995f3d7c6d770):

1. With multiple anchors, it identifies exactly one existing anchor matching the
   callable primary's path, symbol and complete single range. Here that is
   recordSuccessfulUse9–13, not collect.
2. That anchor's excerpt has truncated=false. The helper returns unchanged before
   digest verification or budget trade. This is consistent with its contract.
3. Even hypothetically selecting collect as primary would not suffice: its anchor
   carries class1–13, not method2–12. Its source range and excerpt symbols/start
   differ. Raw row120 proves the file/class range, not an exact method record with
   that ID. A shared digest alone cannot substitute for these identity constraints.

`docs/evidence/multi-source-recovery/README.md` expressly confines recovery to the
callable primary's unique same-range anchor, preserving other excerpts. It does
not promise completion of every truncated alternative or mechanism window.
There is no demonstrated missed invocation of that existing contract here.

## Concrete next step and stopping boundary

There is a narrow design question worth reviewing, not an accepted fix: whether a
selected non-primary method-window may be completed without changing selection,
provided a separate exact method source receipt binds its own ID/path/symbol/full
range/digest and the retained excerpt prefix. First inspect whether such a receipt
survives the existing raw-to-compact path for collect; the saved file anchor alone
is insufficient. Do not fabricate the method identity from its text or class label.

If an existing authoritative method receipt is available, freeze independent
multi-anchor controls before any implementation: partial non-primary method with
space; same-file multiple methods/ambiguous range; already complete primary;
unchanged-prefix changed-tail digest; and genuinely insufficient total/per-source
budget. All unrelated bodies/roles/identities must remain unchanged. This requires
an explicit extension of recovery authority, not removing current equality guards.
If no receipt exists, report that concrete projection gap first. No new architecture,
ranking, primary reassignment, aggregation proof, or original-score gain follows
from this audit. The old exploratory aggregation query is not a frozen acceptance
red and must not be relabeled as one.

## Follow-up: smallest binding path to investigate (not implemented)

Read the current projection chain, not another public query:
`query_callable_evidence.compact_candidate` intentionally emits path/name/range but
not symbol_id or source_digest. `query_callable_range_identity.resolve_candidate_range`
already uses the internal symbol_id when present, requires a unique matching range,
and verifies containment within candidate bounds. These are existing identity
checks, not an ownership or causal proof. `context_compact` currently passes only
`data.wiki_matches` as recovery source_rows. In the saved response this offers the
class/file row, not a collect method receipt.

A bounded design may preserve an internal receipt from that already-selected
candidate/range stage, rather than re-resolve by file/name after compact projection.
Whether the original collect candidate actually had a validated symbol_id is not
established by the saved projected response; the implementer must inspect that
chain before claiming the needed identity already exists. Legacy/name-only ranges
must not silently become exact typed method identities.

The minimum proposed authority is completion of an existing selected partial
method excerpt, not primary promotion or a new anchor: exact candidate ID and full
method bounds; its selected range and excerpt symbol/start; same file digest and
bounded snapshot; range contained in the pre-existing authorized file/class read
window; exact old prefix; and exactly one eligible receipt. Conflicting IDs, two
same-name methods, several ranges or uncertain source receipt must abstain. Do not
change record_type, record_ids, source_ranges, primary, alternatives, roles,
certainty, or source access to manufacture a match. A new private receipt must
remain auditable without impersonating the file/class anchor as a method entity.

Only after a frozen actual public fixture demonstrates the same class-anchor / 
selected-alternative method-window truncation should a transactional completion be
implemented. Preserve all other payload fields and excerpts; honor per-source,
total-character, line and token caps; if full completion does not fit, retain the
original object. No need for rank-diagnostic deletion has been demonstrated in
this saved example. Tests must separately prove absence of output changes when
identity is unknown and when capacity is insufficient. This is a proposed local
projection/recovery extension requiring review, not an existing contract violation
or a semantic aggregation certificate. No fixture/query/code was executed here.
