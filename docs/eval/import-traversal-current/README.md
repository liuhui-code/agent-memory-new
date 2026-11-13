# Public entry import traversal lexical admission

Independent Development, base `fe37131`. The TypeScript protocol/probe were frozen
in 24d3ddf before execution. An ArkTS graph addendum was then frozen in c9cad62,
and both red public outputs committed in 6bd67e4 before production edits.

## Proven defect and actual consumers

`learn-entry --entry Entry.ts --depth 1 --json` learned seven files rather than
Entry plus three genuine dependencies. CommentOnly, TemplateOnly and StringOnly
were linked only by block-comment/plain-template/string import-looking text.
All seven appeared in public `list --type code-file`; actual context/query_handoff
for TemplateOnly retrieved the wrongly learned TemplateOnly and CommentOnly files.
Depth zero correctly learned Entry alone and is a retained positive control.
The ArkTS addendum also produced three false public memory-edge `imports` rows,
alongside the three genuine static named/dynamic-import/require targets.

First faulty layer: resolve_js_imports scanned raw from/import()/require() forms;
resolve_project_imports then fed collect_entry_related_files BFS. The resulting
set goes to write_wiki_index, record_learn_scope and public payload.files. ArkTS
code_wiki_edges also consumes this resolver for file imports. Refresh-scope,
scope-boundary and edge-candidate paths consume it too; these are code references,
not claims that every downstream use had a separately reproduced defect.

## Narrow change

Only the three existing pattern keyword starts must survive the existing strict
lexical mask. Original raw path captures, ordering and duplicates survive; existing
resolver, extensions, depth handling and traversal deduplication are unchanged.
There are no new import syntax forms or module/global binding guarantees. In
particular require-member/shadow semantics, side-effect import support and complete
ECMAScript parsing are outside this change. Regex/division/interpolation/unclosed
input preserves the complete previous file behavior, including old false matches.

Fresh archives now learn exactly four expected files; ArkTS keeps only three real
import edges. All sources remain under the original project: this fix removes
false references and does not expand source access or learning scope.

## Existing archives

upgrade.json uses the same source bytes. Merely installing code retains all seven
files and six import edges. Ordinary merge learn-entry retains the seven learned
files (merge is not deletion) but removes the three false Entry import edges.
This does NOT clean old extra code-file records or promise they stop being
searchable. No replacement or destructive cleanup was performed.

## Validation

Four new tests cover fresh TS/ArkTS public scope and graph, exact unknown legacy
specs, CRLF/raw paths/order/duplicates, and real cyclic traversal at depths0/1/2/8.
Related final command is retained in the stage report below. No full aggregate,
original casepack or holdout was run. Compilation and diff whitespace checks pass.

```
PYTHONPATH=tests:. python -m unittest tests.test_import_traversal_lexical tests.test_import_lexical_admission tests.test_refresh_scope tests.test_scope_boundaries tests.test_learning_coverage_reporting tests.test_context_typed_references -v
```
Final: **37 passed**, zero failures/skips. Initial new+prior lexical run:8 passed.
Runtime files: ecma_import_lexical.py32 lines and code_wiki_imports.py295 lines.

## Separate post-hoc ArkTS UI single-group observation

After the accepted implementation commit 7e22084, the parent requested only
context-arkts-ui-operation-owner (three variants). Before execution, the original
pack's governance was confirmed: split=development, change_policy=editable,
source_isolation=project_neutral, reviewed synthetic lineage. No consumed sealed
holdout was accessed or run. The original query/oracle and production were unchanged.

```
python tools/agent_memory.py eval-context-capability --project . --memory-home /tmp/import-traversal-arkts-eval-memory --cases docs/eval/system-capability-cases.json --case-id context-arkts-ui-operation-owner --json
```

Result in arkts-ui-posthoc.json: **0/3**, one scenario only. Original misses the
expected anchor/source; en-paraphrase and zh-noise recover expected source but
fail precision; en-paraphrase additionally includes a forbidden anchor. All three
remain within context budget. This is not a full gate,
not an original-failure improvement claim, and did not prompt any further edits.
