# Final bounded affirmative Chinese cleanup request adapter

This phase does not fix original05. Fresh unchanged-base and final original05
single-group checks both pass 1/3, with identical average context tokens 1349.6667.
No full suite or new aggregate score is claimed. Existing producer/selection and
English request behavior are unchanged. Source/oracles/thresholds were not edited.

## Independent improvement and preservation
The frozen public fixture gives two actual request-admission defects: zh-head and
zh-source previously returned no compact code anchors and now return the existing
MessageSurface build/helper witness. They are two expressions of one contract,
not two independent architectural defect classes. All ten raw query_handoff values
are exactly baseline; all other eight compact handoffs are exactly baseline,
including the discarded-return control and original negative-scope observation.
`hardened-comparison.json` records these comparisons. This is finite positive
request coverage, not evidence of repairing any original failing variant.

The optional observation prefix is restricted to five nominal input categories
(文章/消息/收据/通知/评论详情). It cannot contain commands, negation or an extra
target; it does not bind source names, fields or causes. Unsupported phrasing
falls through unchanged. All Chinese negative result clauses remain unsupported.
No source identity, path/log protection, digest, excerpt or budget guard changed.

## Rejected intermediate retained, not deployed
The initial adapter consumed a CamelCase negative clause and accepted arbitrary
Han observation text with a blacklist. Review found command-prefix counterexamples
(忽略消息, 另查消息, 同时检查消息) and that existing excluded_code_candidate matches
file_path plus owner_name substrings as well as role tokens, not exact class scope.
The real near-name fixture contains another valid MessageRecordPreview cleanup UI.
Baseline raw contains it but baseline compact already omits it. The rejected
intermediate compact contains MessageSurface only (baseline also has DetailPanel).
Thus omission of MessageRecordPreview is an inherited behavior, not a new red
introduced by this adapter. Nevertheless the filtered trial cannot prove complete
negative scope, so the new route must not authorize that narrower certificate.
Final near-name raw AND compact handoffs equal baseline exactly. The rejected
adapter is retained only as evidence; its exclusion logic is absent from runtime.

A complete new prefilter candidate transport or full-index negative identity
certificate would be a larger contract, not justified merely to turn original05
green. Final implementation rejects all such Chinese exclusion requests, including
ArticleRecord, without exceptions. The earlier semantic-positive protocol remains
frozen; its exclusion form is explicitly outside final supported coverage.

## Tests and reproducibility
52 related tests pass after narrowing (related-hardened.txt). The earlier attempted
suite named nonexistent test_render_recall and recorded one import error; corrected
module test_render_capability_recall passes. All initial logs are retained, not
summed as independent test counts. Tests cover parser negatives, five nominal
prefixes, multiple positive owners, log/path fallback, stale source and exclusion
fallback. Existing source/selection/background suites retain further boundary tests.

Commands: python probe.py.txt --label hardened-after; near-name-probe.py.txt with
baseline/final tools/agent_memory.py; run-original05.py.txt; PYTHONPATH=tests:.
python -m unittest test_render_request_zh test_render_source test_render_selection
 test_render_capability_recall test_background_source test_background_selection -v.
Run from repository root, prefix probe paths with this evidence directory.

Large duplicated raw intermediate/final outputs are in a separate private archive,
with byte hashes in private-raw-manifest.json. Frozen before remains in Git; public
fixture/probes, comparisons, test logs and original single-group outcomes remain
reproducible. Do not interpret private raw absence from Git as a missing failure.
