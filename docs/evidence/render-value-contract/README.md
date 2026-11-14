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
