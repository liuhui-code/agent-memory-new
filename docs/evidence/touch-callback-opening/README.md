# Inline ArkTS member callback ending range

Baseline b9d01e2. Protocol6a64151 was committed before the public init/learn/list/context run; formal regressions were frozen at7227d9b before runtime changes. This is a source-range producer repair, not an original touch/gesture owner-precision improvement.

## Actual public defect and protected output

InlineTouch.onTouch@5 begins on the same line as an enclosing Row block. Public list indexed this callback as5–11, swallowing the later onClick8–10. Its method evidence therefore included onclick/click from the sibling. The split-line equivalent correctly indexed onTouch6–8, and both onClick entities were correct.

The fixed context queries already selected a semantic mechanism window5–7 for InlineTouch and6–8 for SplitTouch. Their outer compact anchors were component ranges. Thus context did NOT demonstrate wrong callback-body output: it is a positive protection control, while list metadata supplied the producer red. We do not relabel that protected output as newly repaired.

## Minimal implementation

The existing block_end API already accepts opening_column. Member callback extraction now supplies the selected callback brace column only when its full-file lexical mask is known, the existing callback_arrow_line-selected arrow is directly followed by whitespace and `{`, and the call-parenthesis balance before that arrow is exactly1. The selected arrow search respects the member-match start column on the same line and column0 on subsequent header lines. The property callback path, callback_arrow_line grammar and block_end scanner are unchanged.

Line-granularity start remains the original header line, so Row/Button text earlier on that line remains in its excerpt/evidence. This repair changes the ending boundary and removes later sibling contamination; it does not claim column-exact excerpts, full parsing, runtime flow or exclusive ownership. The existing limitation where one line closes a callback and starts another block is not redesigned.

## Rejected intermediate and conservative fallback

Review found a real new regression in the first offset candidate: a multiline callback parameter whose type is `() => { ... }` made the inner type arrow appear to open the callback. The candidate ended at the type's closing line3, dropping the real body on later lines. Review controls were separately frozen at9dddcf1, and function-type-candidate-red.txt preserves that result.

The final depth1 admission gate fixes only the offset authorization; it does not search for a later arrow or change the old parser. Both function-type controls now keep their complete legacy ranges7/6. Unknown full-file mask (division, regex or interpolation) also retains complete legacy callback output, including old overly broad ranges. These unsupported cases are not certified absent or fixed.

## Verification and activation

- Formal before:3 tests,2 failures (public list wrong range and known inline string/comment layout),1 pass. Final focused:5 pass; added earlier-arrow/object-type and function-type compatibility controls are documented review additions, not unchanged initial tests.
- Necessary related set:74 tests all pass, zero expected failures. Includes callback lexical admission/multiplicity, property callbacks, callback context, body/header ranges and scan-cost tests. No full suite.
- Fresh public output: InlineTouch.onTouch5–7, true touch terms retained and sibling onclick/click absent. Split/onClick and context semantic windows remain unchanged.
- Same source, same memory: baseline and code-only installation still list end11; normal learn-path merge changes only the target ending to7 and removes sibling terms. Semantic symbol_key, qualified name, file path, digest and start line remain stable; other parsed ranges remain unchanged. SQLite numeric IDs are not used as cross-generation identity promises.
- Original touch-access-safety-owner three variants were run on baseline and candidate without oracle changes. Results are recorded in original-before/after.json; no aggregate/full231 result or original score improvement is claimed.
