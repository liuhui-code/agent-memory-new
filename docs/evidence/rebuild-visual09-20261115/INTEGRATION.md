# Joint local integration of reimplemented 09 and 30

Start: clean d43bae8 on repair/rebuild-after-loss-20261115. This already contained
reviewed output30, its evidence, and the fresh-reimplementation provenance commit.
No 07/37 or other branch was merged in this stage. No remote write or main change.

Mappings:
- visual09 protocol 83ad9cc -> e021b5f
- visual09 candidate/evidence 9bb4c9b -> e9021d5

One textual conflict occurred in query_results.limited_context's signature.
Resolution explicitly retained output30's defer_output_loop_accounting parameter.
Output30 qualification, wrapping, facade/compact handling and accounting remain;
visual09's internal retained-candidate hook was added. Original gitlog text,
including all output30 records, remains verbatim. Nonshared reviewed production
files are byte-identical to their respective reviewed stages; see the machine
checked integration-preservation.json.

## Small mechanical extraction and line limit

Actual git-show counts are 518 lines at d43bae8 and 518 at e9021d5. An earlier
coordination message estimated 520 before measuring; that estimate was incorrect.
Thus 09 did not introduce the whole overrun. Do not carry the independent09
500-line check forward as if it already applied to the combined tree.

The existing qualification and trial-wrapping blocks were mechanically moved to
query_context_trials.py (39 lines). The same lifecycle-before-output qualification
and background-before-lifecycle-before-output wrapping order is preserved, along
with opt-in flags, unchanged selectors, authority objects, guarded shallow copy,
and public function signatures. No request grammar, ranking, source validation,
certificate or budget rule moved or changed. query_results is now 500 lines.
No comments were removed to conceal an overrun. The coordinator separately read
the diff and helper and accepted this limited extraction direction.

## Verification

Before extraction: 100 joint relevant tests pass. After extraction: 104 pass,
including four dedicated orchestration/identity/order controls. Modules cover
output-loop request/source/selection/public, background source/selection, render
source/selection/recall, lifecycle source/selection/public, UI-pair and excerpts.

Final unchanged Development original groups:
- 09: 2/3, preserving original English pass, Chinese repaired pass, English
  paraphrase fail. Chinese complete span 5..16 and 790 estimated compact tokens.
- 30: 3/3, preserving its newly re-established original variant.

Both groups were also checked before extraction with the same results. Independent
09 queries remain 4/4. Output30's generic independent query returns complete
collect lines 2..10; its explicit-name variants retain required paths, but their
class anchors are still not claimed exact-method repairs. No new aggregate score
is calculated. Existing source/evidence limitations and 14 inherited fingerprint
omissions remain documented rather than waived.

Commands used include the joint unittest modules recorded in
integration-related-final.txt, `run.py integration-final` for 09,
`rebuild-output30/run.py integration-after09-final-public`, and the existing
`eval-context-capability --case-id context-process-output-read-loop-owner` on the
unchanged synthetic Development pack. Compilation and git diff --check pass.
No full gate or sealed/holdout evaluation ran. The final integration commit is
saved in a complete-ancestry bundle (HEAD, no prerequisite exclusion), verified
locally, for later authorized persistence. This is new reimplementation, never
recovery of the unavailable 55-commit history.
