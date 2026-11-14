# Render-value binding audit on 6188afe

## Result

The unchanged four-query independent Development fixture remains **1 precision
failure and 3 passing controls**. Generic paths are MessageRecord, MessageSurface,
DisplaySettings. Explicit helper selects MessageSurface; two-source retention
keeps both requested sources plus MessageRecord (not a precision claim); literal
selects DetailPanel. No original case was rerun, no original improvement claimed.

The predeclared discard-return observation produces the same generic anchor paths.
It is not scored: no cleanup-render owner exists in that source variant. It shows
why mere call existence cannot be promoted into a return-to-render dependency.

## Existing identity is real, not missing

Normal learn-path produced exact code_symbol **7 → calls → 8**, build → plainBody,
with semantic-evidence/v1, static, local method call at line 5 and matching source
digest. IDs and stable keys are the same across both snapshots; snapshot digests
correctly differ. build range 4–6, plainBody range 7–9. The digest authenticates the
source version, not which expression consumed a return value.

Both variants have the same typed call relation and operation `call:plainbody`.
The helper has `call:content.replace` and string return signature. The source
text distinguishes `Text(this.plainBody())` from
`this.plainBody(); ... Text(this.content)`, but current metadata does not encode
that argument/result binding. `method_evidence` additionally mentions content in
the discard variant; this is not a typed value identity.

`semantic_ecma.py:291–337` resolves local and typed calls to declaration identities,
not result consumers. `semantic_ecma_mechanisms.py` extracts operation chains,
not return-value uses. No existing return-flow assertion was found dropped in
projection. This is not an existing-contract repair; an ordinary caller edge plus
return signature and a digest cannot authorize excluding other owners.

## Boundary and next step

No runtime/test/oracle/weight changes, no source-name or query-word exception.
Do not publish a post-focus veto or `rather than` exclusion rule from this result.
A proposed narrow expression-binding relation would need explicit lexical,
argument-position, shadowing, nested-call and unknown boundaries, a separately
motivated second defect class if introduced as architecture, and a request-to-role
permission contract. This observation is not that second class. Stop this candidate
rather than adding synthetic noise until an implementation appears justified.
Original repaired count remains 20; no full suite, remote action or CI run.

## Audit correction

The first runner mistakenly requested SQLite tables `records`/`edges`, while the
actual schema uses `code_symbols`/`memory_edges`; its two saved database maps are
empty. Original outputs and run.log remain untouched. `read_index.py` performed
only fresh init + normal learn-path of the exact saved source bytes, then read the
correct tables; **no context query was repeated**. These independently relearned
index snapshots are not misrepresented as the original query archive. Their
source digests match the saved source bytes. All ten public context invocations
(raw + compact for four consumed queries and one discarded query) completed.

## Exact callsite / first representation boundary

Both snapshots resolve caller key `symbol:d2bedc4f31b6507a297acf86` to
callee key `symbol:73641c995d5defc479e3a4d6`. Persisted edge is code_symbol 7→8,
relation calls, line 5, detail local method call; consumed digest is
`174e218a0947b6208e88914c989572a0ef5c85bfcfedd0c144ed814949a20e90`, discarded
`05ec60ccd34bfcd0cfb48319d2ca206fed4557b9dfec7be25493ba645b126342`.
No persisted `callee_source_key`, receiver field, argument spans, column, parent
call ID, returned-expression ID or argument-position field exists on this edge.
The callee identity is carried by target ID/key, not absent altogether.

Read-only `scanner-observation.json` runs existing scan_calls_masked on the exact
saved build slices. Local scanning returns `(2, 'this.plainBody()')` for BOTH;
it has already discarded the containing expression before local-call relation
construction. Generic scanning can still return `Text(this.plainBody())` versus
`Text(this.content)` as separate balanced call strings, but supplies no nesting
relationship or offsets beyond line. Those Text calls are not imported declarations,
so the imported-call branch does not emit a semantic relation for them. Thus the
first confirmed missing *relationship representation* is source-call scanning/
relation construction, not a later SQLite or compact projection erasure. Source
text itself is not erased: it remains separately available.

In both actual compact outputs the MessageSurface anchor (component ID6,
source_range/read_window 2–10) already contains the complete current-worktree
excerpt 1–10, `truncated=false`, query_term_window_within_anchor. The local Agent
can legally inspect these already provided bytes and distinguish the expression
without more reads. The read window and returned decorator prefix differ by one
line, but the complete expression and helper are present. A future bounded
analyzer could inspect this slice with freshness, exact lexical identity and
ambiguity checks; existing evidence does NOT authorize treating the generic
call edge as the resulting proof or Runtime exclusion authority. No claim that
all value-flow information is globally absent is made.

### Budget extraction correction

`binding-summary.json` initially read nonexistent top-level token fields, producing
null values. That historical artifact is preserved. `budget-correction.json` reads
actual saved `compact.output_budget` without rerunning any query: consumed generic
1406, explicit 965, two-source 1283, literal 930; discarded generic 1409. All target
1500 and output_budget.truncated=false. This is not a new acceptance run.
